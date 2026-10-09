import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import LevelCard from './LevelCard';
import { levelAPI } from '../../services/api';

jest.mock('../../services/api', () => ({ levelAPI: { getMine: jest.fn() } }));
jest.mock('../../features/auth/AuthContext', () => ({ useAuth: () => ({ user: { id: 7 } }) }));

const scout = {
    level: 3, title: 'Bug Scout', next_title: 'Bug Hunter', points_to_next: 60, progress: 0.7,
};
const KEY = 'bb_last_level_7';

beforeEach(() => {
    localStorage.clear();
    jest.resetAllMocks();
});

describe('LevelCard', () => {
    test('shows title, progress and points to the next level', () => {
        render(<LevelCard level={scout} />);
        expect(screen.getByText('Bug Scout')).toBeInTheDocument();
        expect(screen.getByText('Level 3')).toBeInTheDocument();
        expect(screen.getByText(/60 pts to/)).toHaveTextContent('Bug Hunter');
        expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '70');
    });

    test('fetches the level when none is passed in', async () => {
        levelAPI.getMine.mockResolvedValue({ data: scout });
        render(<LevelCard />);
        expect(await screen.findByText('Bug Scout')).toBeInTheDocument();
        expect(levelAPI.getMine).toHaveBeenCalledTimes(1);
    });

    test('renders nothing while there is no data, and survives a failed fetch', async () => {
        levelAPI.getMine.mockRejectedValue(new Error('boom'));
        const { container } = render(<LevelCard />);
        await waitFor(() => expect(levelAPI.getMine).toHaveBeenCalled());
        expect(container).toBeEmptyDOMElement();
    });

    test('max level says so', () => {
        render(<LevelCard level={{ level: 8, title: 'Bug Legend', next_title: null, points_to_next: 0, progress: 1 }} />);
        expect(screen.getByText('Max level reached!')).toBeInTheDocument();
        expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '100');
    });

    describe('level-up banner', () => {
        test('the very first visit only records the level', () => {
            render(<LevelCard level={scout} />);
            expect(screen.queryByRole('status')).toBeNull();
            expect(localStorage.getItem(KEY)).toBe('3');
        });

        test('a step up since the last visit is celebrated once', () => {
            localStorage.setItem(KEY, '2');
            const { unmount } = render(<LevelCard level={scout} />);
            expect(screen.getByRole('status')).toHaveTextContent("You're now a Bug Scout");
            expect(localStorage.getItem(KEY)).toBe('3');
            unmount();
            render(<LevelCard level={scout} />);
            expect(screen.queryByRole('status')).toBeNull();
        });

        test('can be dismissed', () => {
            localStorage.setItem(KEY, '1');
            render(<LevelCard level={scout} />);
            userEvent.click(screen.getByRole('button', { name: 'Dismiss' }));
            expect(screen.queryByRole('status')).toBeNull();
        });

        test('dropping a level is not celebrated and does not lower the remembered level', () => {
            localStorage.setItem(KEY, '5');
            render(<LevelCard level={scout} />);
            expect(screen.queryByRole('status')).toBeNull();
            expect(localStorage.getItem(KEY)).toBe('5');
        });

        test('keeps working when storage is blocked', () => {
            const get = jest.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('blocked'); });
            const set = jest.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('blocked'); });
            render(<LevelCard level={scout} />);
            expect(screen.getByText('Bug Scout')).toBeInTheDocument();
            get.mockRestore();
            set.mockRestore();
        });
    });
});
