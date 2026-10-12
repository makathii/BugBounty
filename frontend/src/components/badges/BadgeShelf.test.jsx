import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import BadgeShelf from './BadgeShelf';
import { badgeAPI } from '../../services/api';

jest.mock('../../services/api', () => ({ badgeAPI: { getBadges: jest.fn() } }));
jest.mock('../../features/auth/AuthContext', () => ({ useAuth: () => ({ user: { id: 7 } }) }));

const badge = (key, name, icon, earned) => ({ key, name, icon, earned, description: `${name} desc` });
const response = (badges) => ({
    data: { earned_count: badges.filter((b) => b.earned).length, total: badges.length, badges },
});
const KEY = 'bb_seen_badges_7';
const renderShelf = () => render(<MemoryRouter><BadgeShelf /></MemoryRouter>);

beforeEach(() => {
    localStorage.clear();
    jest.resetAllMocks();
});

describe('BadgeShelf', () => {
    test('shows the count and the earned icons only', async () => {
        badgeAPI.getBadges.mockResolvedValue(response([
            badge('a', 'First Blood', '🩸', true), badge('b', 'Collector', '🐞', false),
        ]));
        renderShelf();
        expect(await screen.findByText('1/2')).toBeInTheDocument();
        expect(screen.getByTitle('First Blood: First Blood desc')).toHaveTextContent('🩸');
        expect(screen.queryByTitle(/Collector/)).toBeNull();
        expect(screen.getByRole('link', { name: 'View all' })).toHaveAttribute('href', '/badges');
    });

    test('invites a first accepted report when nothing is earned', async () => {
        badgeAPI.getBadges.mockResolvedValue(response([badge('a', 'First Blood', '🩸', false)]));
        renderShelf();
        expect(await screen.findByText(/No badges yet/)).toBeInTheDocument();
    });

    test('the first visit records badges without announcing them', async () => {
        badgeAPI.getBadges.mockResolvedValue(response([badge('a', 'First Blood', '🩸', true)]));
        renderShelf();
        await screen.findByText('1/1');
        expect(screen.queryByRole('status')).toBeNull();
        await waitFor(() => expect(JSON.parse(localStorage.getItem(KEY))).toEqual(['a']));
    });

    test('announces only badges earned since the last visit, once', async () => {
        localStorage.setItem(KEY, JSON.stringify(['a']));
        badgeAPI.getBadges.mockResolvedValue(response([
            badge('a', 'First Blood', '🩸', true), badge('b', 'Heavy Hitter', '🔨', true),
        ]));
        const { unmount } = renderShelf();
        const banner = await screen.findByRole('status');
        expect(banner).toHaveTextContent('New badge: 🔨 Heavy Hitter');
        expect(banner).not.toHaveTextContent('First Blood');
        unmount();
        renderShelf();
        await screen.findByText('2/2');
        expect(screen.queryByRole('status')).toBeNull();
    });

    test('the banner can be dismissed', async () => {
        localStorage.setItem(KEY, '[]');
        badgeAPI.getBadges.mockResolvedValue(response([badge('a', 'First Blood', '🩸', true)]));
        renderShelf();
        userEvent.click(await screen.findByRole('button', { name: 'Dismiss' }));
        expect(screen.queryByRole('status')).toBeNull();
    });

    test('renders nothing if badges cannot be loaded', async () => {
        badgeAPI.getBadges.mockRejectedValue(new Error('down'));
        const { container } = renderShelf();
        await waitFor(() => expect(badgeAPI.getBadges).toHaveBeenCalled());
        expect(container).toBeEmptyDOMElement();
    });
});
