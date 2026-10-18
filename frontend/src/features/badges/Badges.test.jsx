import { render, screen } from '@testing-library/react';
import Badges from './Badges';
import { badgeAPI } from '../../services/api';

jest.mock('../../services/api', () => ({ badgeAPI: { getBadges: jest.fn() } }));

const earned = { key: 'a', name: 'First Blood', icon: '🩸', description: 'Get your first report accepted.',
    earned: true, awarded_at: '2026-10-09T10:00:00Z', progress: { current: 1, target: 1 } };
const locked = { key: 'b', name: 'Bug Collector', icon: '🐞', description: 'Get 10 reports accepted.',
    earned: false, awarded_at: null, progress: { current: 3, target: 10 } };

describe('Badges page', () => {
    test('earned badges show their date, locked ones show progress', async () => {
        badgeAPI.getBadges.mockResolvedValue({ data: { earned_count: 1, total: 2, badges: [earned, locked] } });
        render(<Badges />);
        expect(await screen.findByText('1 of 2 earned.', { exact: false })).toBeInTheDocument();
        expect(screen.getByText(/Earned /)).toBeInTheDocument();
        expect(screen.getByText('3 / 10')).toBeInTheDocument();
        const bar = screen.getByRole('progressbar', { name: 'Bug Collector progress' });
        expect(bar).toHaveAttribute('aria-valuenow', '3');
        expect(bar).toHaveAttribute('aria-valuemax', '10');
        expect(bar.firstChild).toHaveStyle({ width: '30%' });
    });

    test('shows a message when badges cannot be loaded', async () => {
        badgeAPI.getBadges.mockRejectedValue(new Error('down'));
        render(<Badges />);
        expect(await screen.findByText(/Could not load your badges/)).toBeInTheDocument();
    });

    test('shows which items a badge unlocks, and whether they are unlocked yet', async () => {
        const reward = { slug: 'halo', name: 'Clean Halo', art: '😇', slot: 'hat', rarity: 'legendary', price: 0, owned: true };
        badgeAPI.getBadges.mockResolvedValue({ data: { earned_count: 1, total: 2, badges: [
            { ...earned, rewards: [reward] },
            { ...locked, rewards: [{ ...reward, slug: 'beetle', name: 'Beetle Buddy', art: '🪲', owned: false }] },
        ] } });
        render(<Badges />);
        expect(await screen.findByTestId('rewards-a')).toHaveTextContent('Unlocked: 😇 Clean Halo');
        expect(screen.getByTestId('rewards-b')).toHaveTextContent('Unlocks: 🪲 Beetle Buddy');
    });
});
