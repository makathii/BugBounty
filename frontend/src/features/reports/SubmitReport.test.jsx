import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom';
import SubmitReport from './SubmitReport';
import api, { reportAPI } from '../../services/api';

jest.mock('../../services/api', () => ({
    __esModule: true,
    default: { get: jest.fn() },
    reportAPI: { createReport: jest.fn() },
}));

const PROGRAMS = [{ id: 1, name: 'Acme Web Platform' }, { id: 3, name: 'TechFlow API' }];
const Where = () => <div data-testid="where">{useLocation().pathname}</div>;

const renderAt = (url) => render(
    <MemoryRouter initialEntries={[url]}>
        <Routes>
            <Route path="/submit" element={<SubmitReport />} />
            <Route path="*" element={<Where />} />
        </Routes>
    </MemoryRouter>
);

const fillAndSubmit = async () => {
    userEvent.type(screen.getByPlaceholderText(/Reflected XSS/), 'A sufficiently long title');
    userEvent.type(screen.getByPlaceholderText(/Describe the vulnerability/), 'd'.repeat(60));
    userEvent.type(screen.getByPlaceholderText(/Navigate to/), 'step one');
    userEvent.type(screen.getByPlaceholderText(/What can an attacker/), 'bad things');
    userEvent.click(screen.getByRole('checkbox'));
    userEvent.click(screen.getByRole('button', { name: 'Submit Report' }));
};

beforeEach(() => {
    jest.resetAllMocks();
    api.get.mockResolvedValue({ data: PROGRAMS });
    window.alert = jest.fn();
});

describe('SubmitReport: the program a report belongs to', () => {
    // The bug: /submit?program=1 ignored the parameter and filed the report under NO program.
    test('a report submitted from a program link is filed under that program', async () => {
        reportAPI.createReport.mockResolvedValue({ data: { id: 9 } });
        renderAt('/submit?program=3');
        await screen.findByPlaceholderText(/Reflected XSS/);
        expect(screen.getByLabelText('Program *')).toHaveValue('3');

        await fillAndSubmit();

        await waitFor(() => expect(reportAPI.createReport).toHaveBeenCalledTimes(1));
        expect(reportAPI.createReport.mock.calls[0][0]).toMatchObject({ program: 3 });
        expect(await screen.findByTestId('where')).toHaveTextContent('/reports');
    });

    test('without a program, nothing can be filed until one is chosen', async () => {
        renderAt('/submit');
        expect(await screen.findByText(/Choose the program you are reporting to/)).toBeInTheDocument();
        expect(screen.queryByPlaceholderText(/Reflected XSS/)).toBeNull();

        userEvent.selectOptions(screen.getByLabelText('Program *'), '1');
        expect(await screen.findByPlaceholderText(/Reflected XSS/)).toBeInTheDocument();
    });

    test('a program the researcher cannot use is called out and shows no form', async () => {
        renderAt('/submit?program=999');
        expect(await screen.findByText(/not available to you/)).toBeInTheDocument();
        expect(screen.queryByPlaceholderText(/Reflected XSS/)).toBeNull();
    });

    test('programs the researcher can see but not report to are not offered', async () => {
        api.get.mockResolvedValue({ data: [
            { id: 1, name: 'Acme Web Platform', user_has_access: true },
            { id: 7, name: 'Private Vault', user_has_access: false },
        ] });
        renderAt('/submit?program=7');
        expect(await screen.findByText(/not available to you/)).toBeInTheDocument();
        const options = within(screen.getByLabelText('Program *')).getAllByRole('option').map((o) => o.textContent);
        expect(options).toContain('Acme Web Platform');
        expect(options).not.toContain('Private Vault');
        expect(screen.queryByPlaceholderText(/Reflected XSS/)).toBeNull();
    });

    test('a failure to load programs is explained', async () => {
        api.get.mockRejectedValue(new Error('down'));
        renderAt('/submit?program=1');
        expect(await screen.findByText(/Could not load programs/)).toBeInTheDocument();
        expect(screen.queryByPlaceholderText(/Reflected XSS/)).toBeNull();
    });

    test('cancel goes back to the program page', async () => {
        renderAt('/submit?program=1');
        await screen.findByPlaceholderText(/Reflected XSS/);
        userEvent.click(screen.getByRole('button', { name: 'Cancel' }));
        expect(await screen.findByTestId('where')).toHaveTextContent('/programs/1');
    });
});

describe('ReportForm: what the server says back', () => {
    const submitWithServerError = async (data, status = 400) => {
        reportAPI.createReport.mockRejectedValue({ response: { status, data } });
        renderAt('/submit?program=1');
        await screen.findByPlaceholderText(/Reflected XSS/);
        await fillAndSubmit();
    };

    test('a program error is shown (it has no field of its own)', async () => {
        await submitWithServerError({ program: ['This program is not accepting submissions.'] });
        expect(await screen.findByRole('alert')).toHaveTextContent('This program is not accepting submissions.');
    });

    test('a permission error such as "verify your email" is shown', async () => {
        await submitWithServerError({ detail: 'Please verify your email before submitting a report.' }, 403);
        expect(await screen.findByRole('alert')).toHaveTextContent('Please verify your email');
    });

    describe('possible duplicates', () => {
        const duplicates = {
            potential_duplicates: [
                { id: null, title: "Another researcher's report", similarity: 0.87, own: false },
                { id: 4, title: 'My earlier XSS', similarity: 0.95, own: true },
            ],
            message: 'Potential duplicate reports found.',
        };

        test('are listed, with only the researcher\'s own reports named', async () => {
            await submitWithServerError(duplicates);
            const panel = await screen.findByTestId('duplicates');
            expect(within(panel).getByText(/Another researcher's report/)).toBeInTheDocument();
            expect(within(panel).getByText('My earlier XSS')).toBeInTheDocument();
            expect(panel).toHaveTextContent('87% similar');
            expect(panel).toHaveTextContent('95% similar');
            expect(panel).not.toHaveTextContent('[object Object]');
        });

        test('"submit anyway" resubmits with the confirmation and then succeeds', async () => {
            await submitWithServerError(duplicates);
            reportAPI.createReport.mockResolvedValue({ data: { id: 11 } });
            userEvent.click(await screen.findByRole('button', { name: /submit anyway/i }));
            await waitFor(() => expect(reportAPI.createReport).toHaveBeenCalledTimes(2));
            expect(reportAPI.createReport.mock.calls[1][0]).toMatchObject({ program: 1, confirm_not_duplicate: true });
            expect(await screen.findByTestId('where')).toHaveTextContent('/reports');
        });

        test('the first attempt does not claim to be confirmed', async () => {
            await submitWithServerError(duplicates);
            expect(reportAPI.createReport.mock.calls[0][0]).not.toHaveProperty('confirm_not_duplicate');
        });
    });
});
