// What a school confirms when it is created (and what the admin of an older school can confirm later).
// The SAME words are kept on the server (backend/app/services/auth_service.py, CONSENT_TEXT) and stored with every confirmation, with this version.
// backend/tests/test_consent.py compares the two, so they cannot drift apart: change both together and raise the version.
export const CONSENT = {
  version: "v1",
  en: "The school has told the children’s parents or guardians that the children’s classwork will be read in this app, and has their permission. Photos are read by an AI and are not kept. Children’s names are never sent to the AI.",
  hi: "स्कूल ने बच्चों के अभिभावकों को बता दिया है कि बच्चों का कक्षा-कार्य इस ऐप में पढ़ा जाएगा, और उनकी अनुमति ले ली है। फ़ोटो AI द्वारा पढ़ी जाती हैं और सहेजी नहीं जातीं। बच्चों के नाम AI को कभी नहीं भेजे जाते।",
};
