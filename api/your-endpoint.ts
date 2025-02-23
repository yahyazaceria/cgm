import type { NextApiRequest, NextApiResponse } from 'next'

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  // Convert your PHP logic to TypeScript
  res.status(200).json({ status: 'ok' })
} 