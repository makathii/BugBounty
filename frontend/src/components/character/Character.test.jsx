import { render, screen } from '@testing-library/react';
import Character from './Character';

const item = (slot, art, extra = {}) => ({ slug: slot, name: `${slot} item`, slot, art, image_url: '', ...extra });

describe('Character', () => {
    test('an empty loadout still draws the mascot', () => {
        const { container } = render(<Character />);
        expect(screen.getByRole('img', { name: 'Character' })).toBeInTheDocument();
        expect(container.querySelector('.ui-character-base')).toBeInTheDocument();
        expect(container.querySelector('.ui-character-hat')).toBeNull();
    });

    test('draws each equipped slot in its own layer', () => {
        const { container } = render(
            <Character
                loadout={{
                    hat: item('hat', '🎩'), face: item('face', '😎'), body: item('body', '🥼'),
                    pet: item('pet', '🐞'), background: item('background', '🌌'),
                }}
            />
        );
        for (const [cls, art] of [['hat', '🎩'], ['face', '😎'], ['body', '🥼'], ['pet', '🐞'], ['bg', '🌌']]) {
            expect(container.querySelector(`.ui-character-${cls}`)).toHaveTextContent(art);
        }
        expect(container.firstChild).toHaveClass('has-background');
    });

    test('an image_url wins over the emoji', () => {
        const { container } = render(
            <Character loadout={{ hat: item('hat', '🎩', { image_url: 'https://cdn.example/hat.png', name: 'Top hat' }) }} />
        );
        const img = container.querySelector('img.ui-character-hat');
        expect(img).toHaveAttribute('src', 'https://cdn.example/hat.png');
        expect(img).toHaveAttribute('alt', 'Top hat');
        expect(container.querySelector('span.ui-character-hat')).toBeNull();
    });

    test('an item without art gets a gift placeholder', () => {
        const { container } = render(<Character loadout={{ hat: item('hat', '') }} />);
        expect(container.querySelector('.ui-character-hat')).toHaveTextContent('🎁');
    });

    test('uses the label and size it is given', () => {
        render(<Character size={50} label="Ada's character" />);
        const el = screen.getByRole('img', { name: "Ada's character" });
        expect(el).toHaveStyle({ width: '50px', height: '50px' });
    });
});
