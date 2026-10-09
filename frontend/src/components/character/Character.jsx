import React from 'react';

// Placeholder mascot until real artwork exists. Items bring their own `art` (an emoji) or
// `image_url`; this component only decides where each slot goes, so swapping in proper
// illustrations later means changing the item data, not this layout.
const BASE = '🧑‍💻';

const Art = ({ item, className }) => {
    if (!item) return null;
    if (item.image_url) {
        return <img className={className} src={item.image_url} alt={item.name} />;
    }
    return <span className={className} role="img" aria-label={item.name}>{item.art || '🎁'}</span>;
};

/**
 * A researcher's character. `loadout` is `{slot: item}` as the API returns it
 * (hat / face / body / pet / background). `size` is the pixel width of the square.
 */
const Character = ({ loadout = {}, size = 120, label }) => {
    const { background, body, face, hat, pet } = loadout;
    return (
        <div
            className={`ui-character${background ? ' has-background' : ''}`}
            style={{ width: size, height: size, fontSize: size * 0.42 }}
            role="img"
            aria-label={label || 'Character'}
        >
            <Art item={background} className="ui-character-layer ui-character-bg" />
            {body && <Art item={body} className="ui-character-layer ui-character-body" />}
            <span className="ui-character-layer ui-character-base" aria-hidden="true">{BASE}</span>
            {face && <Art item={face} className="ui-character-layer ui-character-face" />}
            {hat && <Art item={hat} className="ui-character-layer ui-character-hat" />}
            {pet && <Art item={pet} className="ui-character-layer ui-character-pet" />}
        </div>
    );
};

export default Character;
