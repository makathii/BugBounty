import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import ResearcherProfile from './ResearcherProfile';
import { profileAPI } from '../../services/api';

jest.mock('../../services/api', () => ({
    profileAPI: { getResearcher: jest.fn(), getMySettings: jest.fn(), updateMySettings: jest.fn() },
}));

const profile = (extra = {}) => ({
    username: 'ada', member_since: '2025-03-04T10:00:00Z', bio: 'Fuzzing since 2019', is_self: false, is_public: true,
    level: { level: 3, title: 'Bug Scout' }, lifetime_points: 150, rank: 2,
    stats: { accepted: 4, critical: 1, programs: 2, streak: 3 },
    badges: [{ key: 'first_blood', name: 'First Blood', icon: '🩸', description: 'Get your first report accepted.' }],
    badge_total: 8, loadout: { hat: { slug: 'cap', name: 'Cap', slot: 'hat', rarity: 'common', art: '🧢' } },
    ...extra,
});

const renderPage = (path = '/researchers/ada') => render(
    <MemoryRouter initialEntries={[path]}>
        <Routes><Route path="/researchers/:username" element={<ResearcherProfile />} /></Routes>
    </MemoryRouter>,
);

beforeEach(() => jest.resetAllMocks());

test('shows the character, level, rank, stats and earned badges', async () => {
    profileAPI.getResearcher.mockResolvedValue({ data: profile() });
    renderPage();
    expect(await screen.findByRole('heading', { name: 'ada' })).toBeInTheDocument();
    expect(screen.getByText(/Lv 3/)).toBeInTheDocument();
    expect(screen.getByText('Rank #2')).toBeInTheDocument();
    expect(screen.getByText('Fuzzing since 2019')).toBeInTheDocument();
    expect(screen.getByTestId('profile-badge-first_blood')).toHaveTextContent('First Blood');
    expect(screen.getByText('1/8')).toBeInTheDocument();
    expect(screen.getByRole('img', { name: "ada's character" })).toBeInTheDocument();
    expect(screen.queryByText('Your profile')).toBeNull(); // settings are only for the owner
});

test('a bio is shown as text, never as markup', async () => {
    profileAPI.getResearcher.mockResolvedValue({ data: profile({ bio: '<img src=x onerror=alert(1)>' }) });
    const { container } = renderPage();
    expect(await screen.findByText('<img src=x onerror=alert(1)>')).toBeInTheDocument();
    expect(container.querySelector('img[src="x"]')).toBeNull();
});

test('an unknown or hidden researcher gets a plain "not found"', async () => {
    profileAPI.getResearcher.mockRejectedValue({ response: { status: 404 } });
    renderPage('/researchers/nobody');
    expect(await screen.findByText(/no researcher with that name/i)).toBeInTheDocument();
});

test('other failures say so', async () => {
    profileAPI.getResearcher.mockRejectedValue({ response: { status: 500 } });
    renderPage();
    expect(await screen.findByText(/could not load this profile/i)).toBeInTheDocument();
});

test('the owner can change the bio and hide the page', async () => {
    profileAPI.getResearcher.mockResolvedValue({ data: profile({ is_self: true, bio: '' }) });
    profileAPI.updateMySettings.mockResolvedValue({ data: { bio: 'New intro', is_public: false } });
    renderPage();
    await userEvent.type(await screen.findByLabelText(/short intro/i), 'New intro');
    await userEvent.click(screen.getByRole('checkbox'));
    await userEvent.click(screen.getByRole('button', { name: 'Save' }));
    expect(profileAPI.updateMySettings).toHaveBeenCalledWith({ bio: 'New intro', is_public: false });
    expect(await screen.findByText('Saved.')).toBeInTheDocument();
    expect(screen.getByText(/your profile is hidden/i)).toBeInTheDocument();
});

test('a save error is shown', async () => {
    profileAPI.getResearcher.mockResolvedValue({ data: profile({ is_self: true }) });
    profileAPI.updateMySettings.mockRejectedValue({ response: { data: { bio: ['Ensure this field has no more than 160 characters.'] } } });
    renderPage();
    await userEvent.click(await screen.findByRole('button', { name: 'Save' }));
    await waitFor(() => expect(screen.getByText(/no more than 160/)).toBeInTheDocument());
});
