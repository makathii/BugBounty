import React from 'react';

/** Small "Lv 3 · Bug Scout" tag for lists. Renders nothing without level data. */
const LevelChip = ({ level, title }) => {
    if (!level) return null;
    return (
        <span className="ui-level-chip" title={`Level ${level}: ${title}`}>
            Lv {level}{title ? ` · ${title}` : ''}
        </span>
    );
};

export default LevelChip;
