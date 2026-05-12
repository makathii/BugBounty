// src/services/api.js
import axios from 'axios';

// REACT_APP_API_URL wird in .env.local (lokal) oder Vercel Environment Variables gesetzt.
// Fallback auf localhost:8000 für lokale Entwicklung.
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Add token to requests
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;

        if (error.response?.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true;

            try {
                const refreshToken = localStorage.getItem('refresh_token');
                if (refreshToken) {
                    const response = await axios.post(`${API_BASE_URL}/token/refresh/`, {
                        refresh: refreshToken
                    });

                    const newAccessToken = response.data.access;
                    localStorage.setItem('access_token', newAccessToken);

                    // Retry original request
                    originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
                    return api(originalRequest);
                }
            } catch (refreshError) {
                // Refresh failed, logout user
                localStorage.removeItem('access_token');
                localStorage.removeItem('refresh_token');
                window.location.href = '/login';
            }
        }

        return Promise.reject(error);
    }
);

export const authAPI = {
    login: (data) => api.post('/token/', data),
    refreshToken: (data) => api.post('/token/refresh/', data),
    register: (data) => api.post('/users/register/', data),
    getProfile: () => api.get('/users/profile/'),
    getGroups: () => api.get('/users/groups/'),
    logout: (data) => api.post('/users/logout/', data),
    checkProfileStatus: () => api.get('/users/check-profile/'),
};

export const companyAPI = {
    createCompanyProfile: (data) => api.post('/users/companies/', data),
    getCompanyProfile: () => api.get('/users/companies/my_profile/'),
    updateCompanyProfile: (id, data) => api.put(`/users/companies/${id}/`, data),
    hasCompanyProfile: () => api.get('/users/companies/has_profile/'),

    createProgram: (data) => api.post('/programs/programs/', data), // You'll need to create this endpoint
    getCompanyPrograms: () => api.get('/programs/programs/'), // You'll need to create this endpoint
};

export const reportAPI = {
    getReports: (params = {}) => api.get('/reports/reports/', { params }),

    getReport: (id) => api.get(`/reports/reports/${id}/`),

    createReport: (data) => api.post('/reports/reports/', data),

    updateReport: (id, data) => api.patch(`/reports/reports/${id}/`, data),

    deleteReport: (id) => api.delete(`/reports/reports/${id}/`),

    assignToMe: (id) => api.post(`/reports/reports/${id}/assign_to_me/`),
    acceptReport: (id, data) => api.post(`/reports/reports/${id}/accept/`, data),
    rejectReport: (id, data) => api.post(`/reports/reports/${id}/reject/`, data),
    reopenReport: (id) => api.post(`/reports/reports/${id}/reopen/`),
    changeStatus: (id, data) => api.patch(`/reports/reports/${id}/change_status/`, data),
    submitForReview: (id) => api.post(`/reports/reports/${id}/submit_for_review/`),

    addComment: (id, data) => api.post(`/reports/reports/${id}/comment/`, data),

    getMySubmissions: (params = {}) => api.get('/reports/reports/my_submissions/', { params }),
    getStats: () => api.get('/reports/reports/stats/'),
    getTriageDashboard: () => api.get('/reports/reports/triage_dashboard/'),

    getActivityLogs: (id) => api.get(`/reports/reports/${id}/activity_logs/`),

    getAttachments: (id) => api.get(`/reports/reports/${id}/attachments/`),
    uploadAttachment: (id, data) => api.post(`/reports/reports/${id}/upload_attachment/`, data, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    }),
    downloadAttachment: (id, attId) => api.get(`/reports/reports/${id}/download/${attId}/`, {
        responseType: 'blob',
    }),
};

export const researcherAPI = {
    createResearcherProfile: (data) => api.post('/users/researchers/', data),
    getResearcherProfile: () => api.get('/users/researchers/my_profile/'),
    updateResearcherProfile: (id, data) => api.put(`/users/researchers/${id}/`, data),
};


export const homeAPI = {
    getStats: () => api.get('/home/stats/'),
    getPublicReports: () => api.get('/home/public-reports/'),
    getPrograms: () => api.get('/programs/programs/public/'),
};

export const isAuthenticated = () => {
    return !!localStorage.getItem('access_token');
};

export const getAuthHeaders = () => {
    const token = localStorage.getItem('access_token');
    return token ? { Authorization: `Bearer ${token}` } : {};
};

export default api;