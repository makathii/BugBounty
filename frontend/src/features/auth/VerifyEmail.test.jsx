import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import VerifyEmail from './VerifyEmail';
import api from '../../services/api';

jest.mock('../../services/api', () => ({ __esModule: true, default: { get: jest.fn() } }));

const renderAt = (token = 'abc123') => render(
    <MemoryRouter initialEntries={[`/verify-email/${token}`]}>
        <Routes>
            <Route path="/verify-email/:token" element={<VerifyEmail />} />
            <Route path="/login" element={<div>login page</div>} />
        </Routes>
    </MemoryRouter>
);

beforeEach(() => jest.resetAllMocks());

describe('VerifyEmail', () => {
    test('a successful verification says so and offers the login', async () => {
        api.get.mockResolvedValue({ data: { detail: 'Email verified successfully. You can now log in.' } });
        renderAt();
        expect(await screen.findByText('Email Verified!')).toBeInTheDocument();
        expect(api.get).toHaveBeenCalledWith('/users/verify-email/abc123/');
        expect(screen.getByRole('button', { name: 'Go to Login' })).toBeInTheDocument();
    });

    test('verifies once even though React may run the effect twice', async () => {
        api.get.mockResolvedValue({ data: {} });
        renderAt();
        await screen.findByText('Email Verified!');
        expect(api.get).toHaveBeenCalledTimes(1);
    });

    test('a rejected link is a failure, with the hint that already-verified users can log in', async () => {
        api.get.mockRejectedValue({ response: { status: 400, data: { detail: 'Invalid or expired token' } } });
        renderAt();
        expect(await screen.findByText('Verification Failed')).toBeInTheDocument();
        expect(screen.getByText(/Invalid or expired token/)).toBeInTheDocument();
        expect(screen.getByText(/simply log in/)).toBeInTheDocument();
        expect(screen.queryByText('Email Verified!')).toBeNull();
    });

    // The bug: every error that was not literally "invalid" was reported as success.
    test.each([
        ['the server is unreachable', new Error('Network Error')],
        ['the server errors', { response: { status: 500, data: {} } }],
        ['the server rate-limits', { response: { status: 429, data: { detail: 'Too many requests' } } }],
    ])('never claims success when %s', async (_name, error) => {
        api.get.mockRejectedValue(error);
        renderAt();
        expect(await screen.findByText('Verification Failed')).toBeInTheDocument();
        expect(screen.getByText(/couldn't verify your email right now/)).toBeInTheDocument();
        expect(screen.queryByText('Email Verified!')).toBeNull();
        expect(screen.queryByText(/already verified/i)).toBeNull();
    });
});
