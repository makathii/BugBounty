import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import NotificationBell from './NotificationBell';
import { notificationAPI } from '../../services/api';

jest.mock('../../services/api', () => ({
    notificationAPI: { getAll: jest.fn(), getUnreadCount: jest.fn(), markRead: jest.fn(), markAllRead: jest.fn() },
}));

const note = (id, read, extra = {}) => ({
    id, read, title: `Note ${id}`, message: `Message ${id}`, link: `/reports/${id}`,
    created_at: new Date().toISOString(), ...extra,
});

const renderBell = () => render(
    <MemoryRouter initialEntries={['/']}>
        <NotificationBell />
        <Routes><Route path="*" element={<div data-testid="where" />} /></Routes>
    </MemoryRouter>,
);

beforeEach(() => {
    jest.resetAllMocks();
    notificationAPI.markRead.mockResolvedValue({});
    notificationAPI.markAllRead.mockResolvedValue({});
});

test('shows the unread count on the bell, and nothing when there is none', async () => {
    notificationAPI.getUnreadCount.mockResolvedValue({ data: { unread_count: 3 } });
    renderBell();
    expect(await screen.findByTestId('bell-count')).toHaveTextContent('3');
    expect(screen.getByRole('button', { name: 'Notifications, 3 unread' })).toBeInTheDocument();
});

test('no badge at zero', async () => {
    notificationAPI.getUnreadCount.mockResolvedValue({ data: { unread_count: 0 } });
    renderBell();
    await waitFor(() => expect(notificationAPI.getUnreadCount).toHaveBeenCalled());
    expect(screen.queryByTestId('bell-count')).toBeNull();
});

test('opening lists the latest; clicking one marks it read and counts down', async () => {
    notificationAPI.getUnreadCount.mockResolvedValue({ data: { unread_count: 2 } });
    notificationAPI.getAll.mockResolvedValue({ data: { results: [note(1, false), note(2, true)] } });
    renderBell();
    await screen.findByTestId('bell-count');
    await userEvent.click(screen.getByRole('button', { name: /notifications/i }));
    expect(await screen.findByText('Note 1')).toBeInTheDocument();
    expect(screen.getByText('Note 2')).toBeInTheDocument();

    await userEvent.click(screen.getByText('Note 1'));
    expect(notificationAPI.markRead).toHaveBeenCalledWith(1);
    expect(screen.getByTestId('bell-count')).toHaveTextContent('1');
    expect(screen.queryByText('Note 2')).toBeNull(); // the panel closed
});

test('an already read one is not marked again', async () => {
    notificationAPI.getUnreadCount.mockResolvedValue({ data: { unread_count: 0 } });
    notificationAPI.getAll.mockResolvedValue({ data: [note(2, true)] });
    renderBell();
    await userEvent.click(screen.getByRole('button', { name: /notifications/i }));
    await userEvent.click(await screen.findByText('Note 2'));
    expect(notificationAPI.markRead).not.toHaveBeenCalled();
});

test('"Mark all read" clears the count', async () => {
    notificationAPI.getUnreadCount.mockResolvedValue({ data: { unread_count: 2 } });
    notificationAPI.getAll.mockResolvedValue({ data: { results: [note(1, false), note(2, false)] } });
    renderBell();
    await screen.findByTestId('bell-count');
    await userEvent.click(screen.getByRole('button', { name: /notifications/i }));
    await userEvent.click(await screen.findByRole('button', { name: 'Mark all read' }));
    expect(notificationAPI.markAllRead).toHaveBeenCalled();
    expect(screen.queryByTestId('bell-count')).toBeNull();
});

test('a failing list says so instead of hanging', async () => {
    notificationAPI.getUnreadCount.mockResolvedValue({ data: { unread_count: 1 } });
    notificationAPI.getAll.mockRejectedValue(new Error('down'));
    renderBell();
    await userEvent.click(screen.getByRole('button', { name: /notifications/i }));
    expect(await screen.findByText(/could not load notifications/i)).toBeInTheDocument();
});

test('a failing count request leaves the bell quiet', async () => {
    notificationAPI.getUnreadCount.mockRejectedValue(new Error('offline'));
    renderBell();
    await waitFor(() => expect(notificationAPI.getUnreadCount).toHaveBeenCalled());
    expect(screen.queryByTestId('bell-count')).toBeNull();
});

test('a slow count answer from before a click does not bring the badge back', async () => {
    let resolveSlow;
    notificationAPI.getUnreadCount
        .mockResolvedValueOnce({ data: { unread_count: 1 } })
        .mockImplementationOnce(() => new Promise((resolve) => { resolveSlow = resolve; }));
    notificationAPI.getAll.mockResolvedValue({ data: { results: [note(1, false)] } });
    renderBell();
    await screen.findByTestId('bell-count');
    await userEvent.click(screen.getByRole('button', { name: /notifications/i }));
    await userEvent.click(await screen.findByText('Note 1')); // opening also asked for a fresh count
    resolveSlow({ data: { unread_count: 1 } });                // ...whose answer predates the click
    await waitFor(() => expect(notificationAPI.markRead).toHaveBeenCalled());
    expect(screen.queryByTestId('bell-count')).toBeNull();
});
