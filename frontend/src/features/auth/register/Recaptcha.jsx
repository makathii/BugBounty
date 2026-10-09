import React, { forwardRef, useEffect, useImperativeHandle, useRef } from 'react';

// Site key of the reCAPTCHA v2 ("I'm not a robot") pair. When it is not configured the captcha is
// switched off entirely: nothing is rendered and no token is sent. That only works while the
// backend's RECAPTCHA_SECRET_KEY is empty too (see .env.example); with a secret set and no site key
// the backend answers "Captcha is required".
export const RECAPTCHA_SITE_KEY = process.env.REACT_APP_RECAPTCHA_SITE_KEY || '';
export const captchaEnabled = Boolean(RECAPTCHA_SITE_KEY);

const CALLBACK = '__bugbountyRecaptchaLoaded';
let scriptPromise = null;

// Load Google's script once for the whole app, in explicit-render mode, and resolve when
// `grecaptcha.render` is actually usable (an onload callback, not just the <script> load event).
const loadRecaptchaScript = () => {
    if (window.grecaptcha?.render) return Promise.resolve();
    if (!scriptPromise) {
        scriptPromise = new Promise((resolve, reject) => {
            window[CALLBACK] = resolve;
            const script = document.createElement('script');
            script.src = `https://www.google.com/recaptcha/api.js?render=explicit&onload=${CALLBACK}`;
            script.async = true;
            script.defer = true;
            script.onerror = () => {
                scriptPromise = null; // allow a retry on the next mount
                reject(new Error('Could not load reCAPTCHA'));
            };
            document.head.appendChild(script);
        });
    }
    return scriptPromise;
};

/**
 * The reCAPTCHA checkbox. Parents read it through a ref:
 *   ref.current.getToken()  -> the response token ('' if unsolved or the captcha is disabled)
 *   ref.current.reset()     -> clear the checkbox (tokens are single-use)
 * Renders nothing when no site key is configured.
 */
const Recaptcha = forwardRef(function Recaptcha(_props, ref) {
    const containerRef = useRef(null);
    const widgetId = useRef(null);

    useImperativeHandle(ref, () => ({
        getToken: () => (widgetId.current === null ? '' : window.grecaptcha?.getResponse?.(widgetId.current) || ''),
        reset: () => {
            try {
                if (widgetId.current !== null) window.grecaptcha?.reset?.(widgetId.current);
            } catch {
                /* widget already gone: nothing to reset */
            }
        },
    }), []);

    useEffect(() => {
        if (!captchaEnabled) return undefined;
        let cancelled = false;

        loadRecaptchaScript()
            .then(() => {
                // The container is empty on a first render, and also after StrictMode's
                // mount/unmount/mount cycle in development, which would otherwise render twice.
                if (cancelled || !containerRef.current || containerRef.current.childElementCount > 0) return;
                widgetId.current = window.grecaptcha.render(containerRef.current, { sitekey: RECAPTCHA_SITE_KEY });
            })
            .catch((error) => console.error('reCAPTCHA failed to load:', error));

        return () => {
            cancelled = true;
        };
    }, []);

    if (!captchaEnabled) return null;
    return <div ref={containerRef} className="g-recaptcha" />;
});

export default Recaptcha;
