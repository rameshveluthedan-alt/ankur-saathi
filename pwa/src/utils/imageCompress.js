// Shrink a phone photo before upload: a 5 to 10 MB photo becomes a few hundred KB, which saves mobile data and
// keeps handwriting legible. Falls back to the original file if the browser cannot do it.
// A phone with 2 GB of RAM or less (the browser reports it as deviceMemory, in GB) gets a smaller photo: less memory to decode it, less data to send. Handwriting stays legible at 1200 px.
export function compressionSettings(deviceMemory = (typeof navigator !== 'undefined' ? navigator.deviceMemory : undefined)) {
  return deviceMemory && deviceMemory <= 2 ? { maxSide: 1200, quality: 0.7 } : { maxSide: 1600, quality: 0.8 };
}

export async function compressImage(file, maxSide, quality) {
  const chosen = compressionSettings();
  maxSide = maxSide || chosen.maxSide;
  quality = quality || chosen.quality;
  try {
    if (!file.type.startsWith('image/')) return file;
    const bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' });   // respects the phone's rotation flag
    const scale = Math.min(1, maxSide / Math.max(bitmap.width, bitmap.height));
    const w = Math.round(bitmap.width * scale), h = Math.round(bitmap.height * scale);
    const canvas = document.createElement('canvas');
    canvas.width = w; canvas.height = h;
    canvas.getContext('2d').drawImage(bitmap, 0, 0, w, h);
    if (bitmap.close) bitmap.close();
    const blob = await new Promise(res => canvas.toBlob(res, 'image/jpeg', quality));
    if (!blob || blob.size >= file.size) return file;                                    // never make it bigger
    return new File([blob], (file.name || 'photo').replace(/\.[^.]+$/, '') + '.jpg', { type: 'image/jpeg' });
  } catch (e) {
    return file;
  }
}
