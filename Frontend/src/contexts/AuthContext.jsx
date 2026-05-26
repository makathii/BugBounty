import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import { authAPI, companyAPI } from '../services/api';

const AuthContext = createContext();

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [userGroups, setUserGroups] = useState([]);
    const [hasCompanyProfile, setHasCompanyProfile] = useState(false);

    useEffect(() => {
        checkAuth();
    }, []);

    const loginWithOAuth = async (provider) => {
        try {
            const response = await authAPI.oauthStart(provider);

            if (response.data?.authorize_url) {
                window.location.href = response.data.authorize_url;
            } else {
                throw new Error('No authorization URL returned');
            }
        } catch (error) {
            console.error('OAuth login failed:', error);
            throw error;
        }
    };

    const checkCompanyProfile = async () => {
        try {
            const response = await companyAPI.hasCompanyProfile();
            return response.data.has_company_profile;
        } catch (error) {
            console.error('Error checking company profile:', error);
            return false;
        }
    };

    const checkAuth = useCallback(async () => {
        const token = localStorage.getItem('access_token');
        if (token) {
            try {
                const response = await authAPI.getProfile();
                setUser(response.data);
                setUserGroups(response.data.groups || []);

                if (response.data.groups?.includes('ProgramOwner')) {
                    const hasProfile = await checkCompanyProfile();
                    setHasCompanyProfile(hasProfile);
                }
            } catch (error) {
                console.error('Auth check failed:', error);
                if (error.response?.status === 401) {
                    logout();
                }
            }
        }
        setLoading(false);
    }, []);

    const login = async (username, password) => {
        try {
            const tokenResponse = await authAPI.login({ username, password });
            localStorage.setItem('access_token', tokenResponse.data.access);
            localStorage.setItem('refresh_token', tokenResponse.data.refresh);

            const profileResponse = await authAPI.getProfile();
            setUser(profileResponse.data);
            setUserGroups(profileResponse.data.groups || []);

            if (profileResponse.data.groups?.includes('Company')) {
                const hasProfile = await checkCompanyProfile();
                setHasCompanyProfile(hasProfile);
            }

            return { success: true };
        } catch (error) {
            const errorDetail = error.response?.data?.detail || '';
            let errorMessage = 'Login failed';

            // Check if it's an email verification error
            if (typeof errorDetail === 'string' && errorDetail.toLowerCase().includes('email not verified')) {
                errorMessage = 'Please verify your email address before logging in. Check your inbox for the verification link.';
            } else if (errorDetail) {
                errorMessage = errorDetail;
            } else if (error.response?.data) {
                errorMessage = JSON.stringify(error.response.data);
            }

            return {
                success: false,
                error: errorMessage
            };
        }
    };

    const register = async (userData) => {
        console.log('AuthContext: Registering user:', userData.username);
        try {
            console.log('AuthContext: Calling authAPI.register...');
            const response = await authAPI.register(userData);
            console.log('AuthContext: Registration API response:', response.data);

            // Note: No auto-login anymore - user must verify email first
            // The user is created but is_active=False until email is verified

            return { success: true, data: response.data };
        } catch (error) {
            console.error('AuthContext: Registration failed:', error.response?.data || error.message);
            return {
                success: false,
                error: error.response?.data || 'Registration failed'
            };
        }
    };

    const logout = () => {
        const refreshToken = localStorage.getItem('refresh_token');
        if (refreshToken) {
            authAPI.logout({ refresh_token: refreshToken }).catch(console.error);
        }

        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        setUser(null);
        setUserGroups([]);
        setHasCompanyProfile(false);
    };

    const completeCompanyProfile = async (profileData) => {
        try {
            const response = await companyAPI.createCompanyProfile(profileData);
            setHasCompanyProfile(true);
            return { success: true, data: response.data };
        } catch (error) {
            return {
                success: false,
                error: error.response?.data || 'Failed to create company profile'
            };
        }
    };

    const isTriager = () => userGroups.includes('Triager') || userGroups.includes('Admin');
    const isAdmin = () => userGroups.includes('Admin');
    const isResearcher = () => userGroups.includes('Researcher');
    const isCompany = () => userGroups.includes('ProgramOwner');

    const value = {
        user,
        userGroups,
        loading,
        hasCompanyProfile,
        setHasCompanyProfile,
        login,
        loginWithOAuth,
        register,
        logout,
        completeCompanyProfile,
        isTriager,
        isAdmin,
        isResearcher,
        isCompany,
        checkAuth,
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
};