import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthProvider, useAuth } from './AuthContext';
import { authAPI } from '../../services/api';

jest.mock('../../services/api', () => ({
    authAPI: { getProfile: jest.fn(), logout: jest.fn(), login: jest.fn() },
    companyAPI: { hasCompanyProfile: jest.fn() },
}));

const Probe = () => {
    const { user, logout } = useAuth();
    return (
        <div>
            <span data-testid="who">{user ? user.username : 'nobody'}</span>
            <button onClick={logout}>log out</button>
        </div>
    );
};
const renderProbe = () => render(<AuthProvider><Probe /></AuthProvider>);

beforeEach(() => {
    jest.resetAllMocks();
    localStorage.clear();
});

describe('logout', () => {
    // Regression: the stored tokens were removed BEFORE the request went out, so the server saw an
    // unauthenticated call (401) and never ended the session.
    test('tells the server, with the credentials it is about to discard', async () => {
        localStorage.setItem('access_token', 'access-123');
        localStorage.setItem('refresh_token', 'refresh-456');
        authAPI.getProfile.mockResolvedValue({ data: { username: 'ada', groups: ['Researcher'] } });
        authAPI.logout.mockResolvedValue({});
        renderProbe();
        expect(await screen.findByText('ada')).toBeInTheDocument();

        userEvent.click(screen.getByRole('button', { name: 'log out' }));

        expect(authAPI.logout).toHaveBeenCalledTimes(1);
        expect(authAPI.logout).toHaveBeenCalledWith({ refresh_token: 'refresh-456' }, 'access-123');
        expect(localStorage.getItem('access_token')).toBeNull();
        expect(localStorage.getItem('refresh_token')).toBeNull();
        expect(screen.getByTestId('who')).toHaveTextContent('nobody');
    });

    test('still signs the user out locally when the server cannot be reached', async () => {
        localStorage.setItem('access_token', 'a');
        localStorage.setItem('refresh_token', 'r');
        authAPI.getProfile.mockResolvedValue({ data: { username: 'ada', groups: [] } });
        authAPI.logout.mockRejectedValue(new Error('offline'));
        const quiet = jest.spyOn(console, 'error').mockImplementation(() => {});
        renderProbe();
        await screen.findByText('ada');

        userEvent.click(screen.getByRole('button', { name: 'log out' }));

        await waitFor(() => expect(screen.getByTestId('who')).toHaveTextContent('nobody'));
        expect(localStorage.getItem('access_token')).toBeNull();
        quiet.mockRestore();
    });

    test('does not call the server when nobody was logged in', async () => {
        renderProbe();
        await waitFor(() => expect(screen.getByTestId('who')).toHaveTextContent('nobody'));
        await act(async () => { userEvent.click(screen.getByRole('button', { name: 'log out' })); });
        expect(authAPI.logout).not.toHaveBeenCalled();
    });
});
