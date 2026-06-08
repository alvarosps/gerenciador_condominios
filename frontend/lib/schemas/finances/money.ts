import { z } from 'zod';

/** Decimal money arrives from the backend as a string; convert to number at the boundary. */
export const moneyField = z.union([z.string(), z.number()]).transform((val) => Number(val));

/** Money field quantized to 2 decimal places (ROUND_HALF_UP-ish) at the boundary (design §4). */
export const moneyFieldRounded = z
  .union([z.string(), z.number()])
  .transform((val) => Math.round(Number(val) * 100) / 100);

/** Condominium reference as serialized by CondominiumSimpleSerializer ({ id, name }). */
export const condominiumRefSchema = z.object({
  id: z.number(),
  name: z.string(),
});
