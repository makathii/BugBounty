import { render, screen, within, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Store from './Store';
import { storeAPI } from '../../services/api';

jest.mock('../../services/api', () => ({
    storeAPI: {
        getItems: jest.fn(), getInventory: jest.fn(), getLoadout: jest.fn(),
        purchase: jest.fn(), equip: jest.fn(), unequip: jest.fn(),
    },
}));

const item = (slug, name, extra = {}) => ({
    id: slug, slug, name, description: `${name} desc`, slot: 'hat', slot_display: 'Hat',
    rarity: 'common', rarity_display: 'Common', price: 40, min_level: 1, art: '🎩', image_url: '',
    owned: false, equipped: false, locked: false, can_afford: true, ...extra,
});
const shopOf = (items, balance = 265, level = 3) => ({ data: { items, balance, level } });
const setup = ({ items = [], inventory = [], loadout = {}, balance = 265 } = {}) => {
    storeAPI.getItems.mockResolvedValue(shopOf(items, balance));
    storeAPI.getInventory.mockResolvedValue({ data: inventory });
    storeAPI.getLoadout.mockResolvedValue({ data: loadout });
};
const card = (name) => screen.getByText(name, { selector: 'strong' }).closest('.ui-item-card');

beforeEach(() => {
    jest.resetAllMocks();
    window.confirm = jest.fn(() => true);
});

describe('Store: the shop', () => {
    test('lists items with prices and shows the balance', async () => {
        setup({ items: [item('cap', 'Party Hat'), item('starter', 'Starter Cap', { price: 0 })] });
        render(<Store />);
        expect(await screen.findByText('Party Hat')).toBeInTheDocument();
        expect(screen.getByText('265 pts', { selector: 'strong' })).toBeInTheDocument();
        expect(within(card('Party Hat')).getByText('40 pts')).toBeInTheDocument();
        expect(within(card('Starter Cap')).getByText('Free')).toBeInTheDocument();
    });

    test('each unavailable state says why', async () => {
        setup({ items: [
            item('buy', 'Affordable'),
            item('gated', 'Gated', { locked: true, min_level: 4, can_afford: true }),
            item('pricey', 'Pricey', { price: 300, can_afford: false }),
            item('mine', 'Mine', { owned: true }),
        ] });
        render(<Store />);
        await screen.findByText('Affordable');
        expect(within(card('Affordable')).getByRole('button', { name: 'Buy' })).toBeEnabled();
        const gated = within(card('Gated')).getByRole('button', { name: 'Level 4 needed' });
        expect(gated).toBeDisabled();
        expect(within(card('Pricey')).getByRole('button', { name: '35 pts short' })).toBeDisabled();
        expect(within(card('Mine')).getByRole('button', { name: 'Wear' })).toBeEnabled();
        expect(within(card('Mine')).queryByRole('button', { name: 'Buy' })).toBeNull();
    });

    test('a free item says so on its button', async () => {
        setup({ items: [item('starter', 'Starter Cap', { price: 0 })] });
        render(<Store />);
        await screen.findByText('Starter Cap');
        expect(within(card('Starter Cap')).getByRole('button', { name: 'Get it free' })).toBeInTheDocument();
    });

    test('the slot filter narrows the list', async () => {
        setup({ items: [item('h', 'A Hat'), item('p', 'A Pet', { slot: 'pet', slot_display: 'Pet' })] });
        render(<Store />);
        await screen.findByText('A Hat');
        userEvent.click(screen.getByRole('button', { name: 'Pets' }));
        expect(screen.queryByText('A Hat')).toBeNull();
        expect(screen.getByText('A Pet')).toBeInTheDocument();
        userEvent.click(screen.getByRole('button', { name: 'All' }));
        expect(screen.getByText('A Hat')).toBeInTheDocument();
    });

    test('an empty shop has a friendly message', async () => {
        setup();
        render(<Store />);
        expect(await screen.findByText(/Nothing for sale/)).toBeInTheDocument();
    });

    test('a failed load offers a retry that recovers', async () => {
        storeAPI.getItems.mockRejectedValueOnce(new Error('down'));
        storeAPI.getInventory.mockResolvedValue({ data: [] });
        storeAPI.getLoadout.mockResolvedValue({ data: {} });
        render(<Store />);
        expect(await screen.findByText(/Could not load the store/)).toBeInTheDocument();
        storeAPI.getItems.mockResolvedValue(shopOf([item('cap', 'Party Hat')]));
        userEvent.click(screen.getByRole('button', { name: 'Retry' }));
        expect(await screen.findByText('Party Hat')).toBeInTheDocument();
    });
});

describe('Store: buying', () => {
    test('asks for confirmation, buys, thanks you and refreshes', async () => {
        setup({ items: [item('cap', 'Party Hat')] });
        storeAPI.purchase.mockResolvedValue({ data: {} });
        render(<Store />);
        await screen.findByText('Party Hat');
        storeAPI.getItems.mockResolvedValue(shopOf([item('cap', 'Party Hat', { owned: true })], 225));
        userEvent.click(within(card('Party Hat')).getByRole('button', { name: 'Buy' }));
        expect(window.confirm).toHaveBeenCalledWith('Buy Party Hat for 40 pts?');
        expect(await screen.findByRole('status')).toHaveTextContent('You bought Party Hat');
        expect(storeAPI.purchase).toHaveBeenCalledWith('cap');
        expect(await screen.findByRole('button', { name: 'Wear' })).toBeInTheDocument();
        expect(screen.getByText('225 pts', { selector: 'strong' })).toBeInTheDocument();
    });

    test('declining the confirmation buys nothing', async () => {
        setup({ items: [item('cap', 'Party Hat')] });
        window.confirm.mockReturnValue(false);
        render(<Store />);
        await screen.findByText('Party Hat');
        userEvent.click(within(card('Party Hat')).getByRole('button', { name: 'Buy' }));
        expect(storeAPI.purchase).not.toHaveBeenCalled();
    });

    test.each([
        [{ code: 'insufficient_points', balance: 10, needed: 40 }, 'Not enough points: you have 10, this costs 40.'],
        [{ code: 'level_too_low', required_level: 4, level: 3 }, 'You need to be level 4 for this (you are level 3).'],
        [{ code: 'already_owned' }, 'You already own this item.'],
        [{ code: 'item_unavailable' }, 'This item is no longer for sale.'],
        [{ error: 'Custom server message' }, 'Custom server message'],
    ])('explains a failed purchase (%j)', async (body, message) => {
        setup({ items: [item('cap', 'Party Hat')] });
        storeAPI.purchase.mockRejectedValue({ response: { data: body } });
        render(<Store />);
        await screen.findByText('Party Hat');
        userEvent.click(within(card('Party Hat')).getByRole('button', { name: 'Buy' }));
        const toast = await screen.findByRole('status');
        expect(toast).toHaveTextContent(message);
        expect(toast).toHaveClass('is-error');
    });

    test('a network failure still shows a message', async () => {
        setup({ items: [item('cap', 'Party Hat')] });
        storeAPI.purchase.mockRejectedValue(new Error('offline'));
        render(<Store />);
        await screen.findByText('Party Hat');
        userEvent.click(within(card('Party Hat')).getByRole('button', { name: 'Buy' }));
        expect(await screen.findByRole('status')).toHaveTextContent(/Something went wrong/);
    });
});

describe('Store: wearing and trying on', () => {
    const hat = { slug: 'cap', name: 'Party Hat', slot: 'hat', rarity: 'common', art: '🥳', image_url: '' };

    test('wear sends the request and updates the character', async () => {
        setup({ items: [item('cap', 'Party Hat', { owned: true, art: '🥳' })], inventory: [item('cap', 'Party Hat', { owned: true })] });
        storeAPI.equip.mockImplementation(async () => {
            storeAPI.getLoadout.mockResolvedValue({ data: { hat } }); // the server now says it is worn
            return { data: { hat } };
        });
        const { container } = render(<Store />);
        await screen.findByText('Party Hat');
        expect(container.querySelector('.ui-store-side .ui-character-hat')).toBeNull();
        userEvent.click(within(card('Party Hat')).getByRole('button', { name: 'Wear' }));
        await waitFor(() => expect(storeAPI.equip).toHaveBeenCalledWith('cap'));
        await waitFor(() => expect(container.querySelector('.ui-store-side .ui-character-hat')).toHaveTextContent('🥳'));
    });

    test('an item already worn offers "Take off"', async () => {
        setup({ items: [item('cap', 'Party Hat', { owned: true })], loadout: { hat } });
        storeAPI.unequip.mockResolvedValue({ data: {} });
        render(<Store />);
        await screen.findByText('Party Hat');
        userEvent.click(within(card('Party Hat')).getByRole('button', { name: 'Take off' }));
        await waitFor(() => expect(storeAPI.unequip).toHaveBeenCalledWith('cap'));
    });

    test('"Try on" previews without buying, and can be undone', async () => {
        setup({ items: [item('cap', 'Party Hat', { art: '🥳' })] });
        const { container } = render(<Store />);
        await screen.findByText('Party Hat');
        userEvent.click(within(card('Party Hat')).getByRole('button', { name: 'Try on' }));
        expect(container.querySelector('.ui-store-side .ui-character-hat')).toHaveTextContent('🥳');
        expect(screen.getByText(/Trying on/)).toBeInTheDocument();
        userEvent.click(within(card('Party Hat')).getByRole('button', { name: 'Undo try-on' }));
        expect(container.querySelector('.ui-store-side .ui-character-hat')).toBeNull();
        expect(storeAPI.purchase).not.toHaveBeenCalled();
        expect(storeAPI.equip).not.toHaveBeenCalled();
    });

    test('"Reset preview" clears every try-on', async () => {
        setup({ items: [item('a', 'Hat A'), item('b', 'Face B', { slot: 'face', slot_display: 'Face', art: '😎' })] });
        const { container } = render(<Store />);
        await screen.findByText('Hat A');
        userEvent.click(within(card('Hat A')).getByRole('button', { name: 'Try on' }));
        userEvent.click(within(card('Face B')).getByRole('button', { name: 'Try on' }));
        expect(container.querySelectorAll('.ui-store-side .ui-character-layer:not(.ui-character-base)')).toHaveLength(2);
        userEvent.click(screen.getByRole('button', { name: 'Reset preview' }));
        expect(container.querySelectorAll('.ui-store-side .ui-character-layer:not(.ui-character-base)')).toHaveLength(0);
    });

    test('"My items" lists only what you own', async () => {
        setup({
            items: [item('a', 'Shop Only'), item('b', 'Owned One', { owned: true })],
            inventory: [item('b', 'Owned One', { owned: true })],
        });
        render(<Store />);
        await screen.findByText('Shop Only');
        userEvent.click(screen.getByRole('button', { name: 'My items (1)' }));
        expect(screen.queryByText('Shop Only')).toBeNull();
        expect(screen.getByText('Owned One')).toBeInTheDocument();
    });

    test('"My items" is friendly when empty', async () => {
        setup({ items: [item('a', 'Shop Only')] });
        render(<Store />);
        await screen.findByText('Shop Only');
        userEvent.click(screen.getByRole('button', { name: 'My items (0)' }));
        expect(screen.getByText(/do not own anything/)).toBeInTheDocument();
    });
});
