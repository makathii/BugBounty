import { render, screen } from '@testing-library/react';
import App from './App';

// Smoke test: the whole app (router, auth provider, every route's imports) loads and an
// anonymous visitor lands on the public home page with its calls to action.
test('renders the public home page for a visitor', async () => {
    render(<App />);
    expect(await screen.findByRole('link', { name: 'Start Hunting' })).toHaveAttribute('href', '/register/researcher');
    expect(screen.getByRole('link', { name: /Secure Your Product/ })).toHaveAttribute('href', '/register/company');
});
