// Points are the platform's currency: researchers earn them for accepted reports
// and (soon) spend them in the store. One formatter so every page says it the same way.

export const formatPoints = (value) => `${(Number(value) || 0).toLocaleString()} pts`;
