// Offer backup codes as a plain-text download (they are only ever shown once).
export const downloadBackupCodes = (codes) => {
    const blob = new Blob([codes.join('\n') + '\n'], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'bugbounty-backup-codes.txt';
    link.click();
    URL.revokeObjectURL(url);
};
