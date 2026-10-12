import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ReportDecisionModal from './ReportDecisionModal';

const report = { id: 4, title: 'XSS in profile', severity: 'medium' };
const setup = (mode, onSubmit = jest.fn().mockResolvedValue(undefined)) => {
    const onClose = jest.fn();
    render(<ReportDecisionModal mode={mode} report={report} onSubmit={onSubmit} onClose={onClose} />);
    return { onSubmit, onClose };
};

describe('accepting', () => {
    test('needs a note before anything is sent', async () => {
        const { onSubmit } = setup('accept');
        await userEvent.click(screen.getByRole('button', { name: 'Accept report' }));
        expect(await screen.findByRole('alert')).toHaveTextContent(/short note/i);
        expect(onSubmit).not.toHaveBeenCalled();
    });

    test('sends the notes, the chosen severity and the bonus as a number', async () => {
        const { onSubmit } = setup('accept');
        await userEvent.type(screen.getByLabelText(/verification notes/i), 'Reproduced.');
        await userEvent.selectOptions(screen.getByLabelText(/severity/i), 'high');
        await userEvent.clear(screen.getByLabelText(/bonus points/i));
        await userEvent.type(screen.getByLabelText(/bonus points/i), '25');
        await userEvent.click(screen.getByRole('button', { name: 'Accept report' }));
        expect(onSubmit).toHaveBeenCalledWith({ verification_notes: 'Reproduced.', severity: 'high', bonus_points: 25 });
    });

    test.each(['-1', '1.5', 'abc', '1001'])('refuses a bonus of %s', async (bad) => {
        const { onSubmit } = setup('accept');
        await userEvent.type(screen.getByLabelText(/verification notes/i), 'ok');
        await userEvent.clear(screen.getByLabelText(/bonus points/i));
        await userEvent.type(screen.getByLabelText(/bonus points/i), bad);
        await userEvent.click(screen.getByRole('button', { name: 'Accept report' }));
        expect(await screen.findByRole('alert')).toHaveTextContent(/whole number from 0 to 1000/i);
        expect(onSubmit).not.toHaveBeenCalled();
    });

    test('shows the server error and stays open for another try', async () => {
        const { onClose } = setup('accept', jest.fn().mockResolvedValue('Report cannot be accepted in current status'));
        await userEvent.type(screen.getByLabelText(/verification notes/i), 'ok');
        await userEvent.click(screen.getByRole('button', { name: 'Accept report' }));
        expect(await screen.findByRole('alert')).toHaveTextContent('cannot be accepted');
        expect(screen.getByRole('button', { name: 'Accept report' })).toBeEnabled();
        expect(onClose).not.toHaveBeenCalled();
    });
});

describe('rejecting', () => {
    test('only asks for a reason', async () => {
        const { onSubmit } = setup('reject');
        expect(screen.queryByLabelText(/bonus/i)).toBeNull();
        await userEvent.click(screen.getByRole('button', { name: 'Reject report' }));
        expect(await screen.findByRole('alert')).toHaveTextContent(/why it was rejected/i);
        await userEvent.type(screen.getByLabelText(/reason for rejecting/i), 'Duplicate of #3');
        await userEvent.click(screen.getByRole('button', { name: 'Reject report' }));
        expect(onSubmit).toHaveBeenCalledWith({ rejection_reason: 'Duplicate of #3' });
    });
});

test('Escape and Cancel close it', async () => {
    const { onClose } = setup('reject');
    await userEvent.keyboard('{Escape}');
    await userEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(onClose).toHaveBeenCalledTimes(2);
});
