import { render, screen } from '@testing-library/react';
import LevelChip from './LevelChip';

describe('LevelChip', () => {
    test('shows level and title', () => {
        render(<LevelChip level={3} title="Bug Scout" />);
        expect(screen.getByText('Lv 3 · Bug Scout')).toBeInTheDocument();
    });

    test('works without a title', () => {
        render(<LevelChip level={2} />);
        expect(screen.getByText('Lv 2')).toBeInTheDocument();
    });

    test('renders nothing without level data', () => {
        const { container } = render(<LevelChip />);
        expect(container).toBeEmptyDOMElement();
    });
});
