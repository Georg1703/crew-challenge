/** A short tap of the phone's vibration motor (Android); nothing where it is not supported. */
export function tap(): void {
  try {
    navigator.vibrate?.(10);
  } catch {
    // Some browsers throw when vibration is blocked; feedback is a nicety, never required.
  }
}
