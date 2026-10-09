import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import Wallet from './Wallet';
import { walletAPI } from '../../services/api';

jest.mock('../../services/api', () => ({ walletAPI: { getWallet: jest.fn(), getTransactions: jest.fn() } }));
jest.mock('../../components/levels/LevelCard', () => () => <div data-testid="level-card" />);

const wallet = { balance: 215, lifetime_earned: 240, total_spent: 50, level: { level: 3 } };
const tx = (id, amount, reason, kind = 'purchase') => ({
    id, amount, reason, kind, kind_display: kind[0].toUpperCase() + kind.slice(1), created_at: '2026-10-09T10:00:00Z',
});
const renderWallet = () => render(<MemoryRouter><Wallet /></MemoryRouter>);

beforeEach(() => jest.resetAllMocks());

describe('Wallet', () => {
    test('shows balance, lifetime earned, spent and the activity', async () => {
        walletAPI.getWallet.mockResolvedValue({ data: wallet });
        walletAPI.getTransactions.mockResolvedValue({
            data: { count: 2, results: [tx(2, 25, 'Welcome gift', 'adjustment'), tx(1, -50, 'Party hat')] },
        });
        renderWallet();
        expect(await screen.findByText('215 pts')).toBeInTheDocument();
        expect(screen.getByText('240 pts')).toBeInTheDocument();
        expect(screen.getByText('50 pts')).toBeInTheDocument();
        expect(screen.getByText('+25 pts')).toBeInTheDocument();
        expect(screen.getByText('-50 pts')).toBeInTheDocument();
        expect(screen.getByTestId('level-card')).toBeInTheDocument();
        expect(screen.queryByRole('button', { name: 'Show more' })).toBeNull();
    });

    test('an empty history points researchers at programs', async () => {
        walletAPI.getWallet.mockResolvedValue({ data: { ...wallet, total_spent: 0 } });
        walletAPI.getTransactions.mockResolvedValue({ data: { count: 0, results: [] } });
        renderWallet();
        expect(await screen.findByText(/Nothing spent yet/)).toBeInTheDocument();
        expect(screen.getByRole('link', { name: 'find a program' })).toHaveAttribute('href', '/programs');
    });

    test('"Show more" loads the next page from the right offset', async () => {
        walletAPI.getWallet.mockResolvedValue({ data: wallet });
        walletAPI.getTransactions
            .mockResolvedValueOnce({ data: { count: 3, results: [tx(3, -1, 'third'), tx(2, -1, 'second')] } })
            .mockResolvedValueOnce({ data: { count: 3, results: [tx(1, -1, 'first')] } });
        renderWallet();
        userEvent.click(await screen.findByRole('button', { name: 'Show more' }));
        expect(await screen.findByText('first')).toBeInTheDocument();
        expect(walletAPI.getTransactions).toHaveBeenLastCalledWith({ limit: 25, offset: 2 });
        expect(screen.queryByRole('button', { name: 'Show more' })).toBeNull();
    });

    test('a failed load offers a retry that recovers', async () => {
        walletAPI.getWallet.mockRejectedValueOnce(new Error('down')).mockResolvedValue({ data: wallet });
        walletAPI.getTransactions.mockResolvedValue({ data: { count: 0, results: [] } });
        renderWallet();
        expect(await screen.findByText(/Could not load your wallet/)).toBeInTheDocument();
        userEvent.click(screen.getByRole('button', { name: 'Retry' }));
        expect(await screen.findByText('215 pts')).toBeInTheDocument();
    });
});
