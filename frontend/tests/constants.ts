/**
 * Shared test-only credentials.
 *
 * Generated at module load so no password literal lives in source (avoids false-positive secret
 * scanning). They carry no security relevance and only drive the MSW auth mocks + auth-hook tests.
 * The two values are distinct, so the "wrong" password never accidentally matches the valid one.
 */
export const TEST_PASSWORD = `pw-${crypto.randomUUID()}`;
export const TEST_PASSWORD_WRONG = `pw-${crypto.randomUUID()}`;
