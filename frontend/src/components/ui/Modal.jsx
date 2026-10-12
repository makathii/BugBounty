import React, { useEffect, useRef } from 'react';

// A small accessible dialog: Esc and a click on the backdrop close it, focus moves into it and
// returns to whatever opened it. Content goes in children; `footer` holds the buttons.
const Modal = ({ title, onClose, children, footer, busy = false }) => {
    const panel = useRef(null);

    useEffect(() => {
        const opener = document.activeElement;
        const first = panel.current?.querySelector('input, textarea, select, button:not([data-close])');
        (first || panel.current)?.focus();
        const onKey = (e) => { if (e.key === 'Escape' && !busy) onClose(); };
        document.addEventListener('keydown', onKey);
        return () => {
            document.removeEventListener('keydown', onKey);
            if (opener && opener.focus) opener.focus();
        };
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    return (
        <div className="ui-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget && !busy) onClose(); }}>
            <div className="ui-modal" role="dialog" aria-modal="true" aria-label={title} ref={panel} tabIndex={-1}>
                <div className="ui-modal-head">
                    <h2 className="ui-section-title" style={{ margin: 0 }}>{title}</h2>
                    <button type="button" data-close className="ui-btn ui-btn--ghost ui-btn--sm" onClick={onClose}
                            disabled={busy} aria-label="Close">×</button>
                </div>
                <div className="ui-modal-body">{children}</div>
                {footer && <div className="ui-modal-foot">{footer}</div>}
            </div>
        </div>
    );
};

export default Modal;
