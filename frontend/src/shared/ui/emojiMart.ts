/**
 * Emoji Mart in one lazy chunk (`emojiMart-*.js`): the picker and its native emoji data. Only
 * `EmojiPicker` imports it, with `import()`, and the service worker does not precache it.
 */
export { Picker } from "emoji-mart";
export { default as data } from "@emoji-mart/data";
