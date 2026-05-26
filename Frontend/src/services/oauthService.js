import api from './api';

export const startOAuthLogin = async (provider, next = '/') => {
    try {
        const response = await api.get(
            `/users/oauth/${provider}/start/`,
            {
                params: { next }
            }
        );

        return {
            success: true,
            authorizeUrl: response.data.authorize_url
        };
    } catch (error) {
        return {
            success: false,
            error:
                error.response?.data?.detail ||
                'OAuth login failed'
        };
    }
};