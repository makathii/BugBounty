import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const OAuthSuccess = () => {
    const navigate = useNavigate();
    const { checkAuth } = useAuth();

    useEffect(() => {
        const finishLogin = async () => {
            try {
                await checkAuth();
                navigate('/dashboard');
            } catch (error) {
                console.error('OAuth auth sync failed:', error);
                navigate('/login');
            }
        };

        finishLogin();
    }, [checkAuth, navigate]);

    return (
        <div style={{ padding: '2rem', textAlign: 'center' }}>
            <h2>Signing you in...</h2>
        </div>
    );
};

export default OAuthSuccess;