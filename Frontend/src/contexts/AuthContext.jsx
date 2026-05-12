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

                if (response.data.groups?.includes('Company')) {
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
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => {
        checkAuth();
    }, [checkAuth]);

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
            return {
                success: false,
                error: error.response?.data?.detail || 'Login failed'
            };
        }
    };

    const register = async (userData) => {
        console.log('AuthContext: Registering user:', userData.username);
        try {
            console.log('AuthContext: Calling authAPI.register...');
            const response = await authAPI.register(userData);
            console.log('AuthContext: Registration API response:', response.data);

            if (response.data) {
                console.log('AuthContext: Attempting auto-login...');
                const tokenResponse = await authAPI.login({
                    username: userData.username,
                    password: userData.password
                });
                console.log('AuthContext: Auto-login successful');

                localStorage.setItem('access_token', tokenResponse.data.access);
                localStorage.setItem('refresh_token', tokenResponse.data.refresh);

                console.log('AuthContext: Getting user profile...');
                const profileResponse = await authAPI.getProfile();
                console.log('AuthContext: Profile loaded:', profileResponse.data);

                setUser(profileResponse.data);
                setUserGroups(profileResponse.data.groups || []);

                console.log('AuthContext: User state updated');
            }

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
    const isCompany = () => userGroups.includes('Company');

    const value = {
        user,
        userGroups,
        loading,
        hasCompanyProfile,
        setHasCompanyProfile,
        login,
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