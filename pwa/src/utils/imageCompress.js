// Shrink a phone photo before upload: a 5 to 10 MB photo becomes a few hundred KB, which saves mobile data and
// keeps handwriting legible. Falls back to the original file if the browser cannot do it.
export async function compressImage(file, maxSide = 1600, quality = 0.8) {
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
