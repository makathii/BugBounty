import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: { 'Content-Type': 'application/json' },
});

// ---------------------------------------------------------------------------
// Request interceptor — attach JWT
// ---------------------------------------------------------------------------

api.interceptors.request.use((config) => {
    const token = localStorage.getItem('access_token');
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
});

// ---------------------------------------------------------------------------
// Response interceptor — auto-refresh on 401 (registered ONCE)
// ---------------------------------------------------------------------------

api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const original = error.config;

        if (error.response?.status === 401 && !original._retry) {
            original._retry = true;

            try {
                const refresh = localStorage.getItem('refresh_token');
                if (!refresh) throw new Error('No refresh token');

                const { data } = await axios.post(`${API_BASE_URL}/token/refresh/`, { refresh });
                localStorage.setItem('access_token', data.access);
                original.headers.Authorization = `Bearer ${data.access}`;
                return api(original);
            } catch {
                localStorage.removeItem('access_token');
                localStorage.removeItem('refresh_token');
                window.location.href = '/login';
            }
        }

        // Log errors only in development
        if (process.env.NODE_ENV === 'development') {
            console.error(`[API] ${error.config?.method?.toUpperCase()} ${error.config?.url}`, {
                status: error.response?.status,
                data: error.response?.data,
            });
        }

        return Promise.reject(error);
    }
);

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export const authAPI = {
    login:                (data) => api.post('/token/', data),
    refreshToken:         (data) => api.post('/token/refresh/', data),
    register:             (data) => api.post('/users/register/', data),
    getProfile:           ()     => api.get('/users/profile/'),
    updateProfile:        (data) => api.patch('/users/profile/', data),
    getGroups:            ()     => api.get('/users/groups/'),
    logout:               (data) => api.post('/users/logout/', data),
    verifyEmail:          (token)=> api.get(`/users/verify-email/${token}/`),
    resendVerification:   (email) => api.post('/users/resend-verification/', { email }),

    // Password reset: the request always answers 200 (no account enumeration)
    requestPasswordReset: (email) => api.post('/users/password-reset/', { email }),
    confirmPasswordReset: (token, password, password2) =>
        api.post('/users/password-reset/confirm/', { token, password, password2 }),

    // OAuth
    oauthStart: (provider, next = window.location.origin + '/oauth/success') =>
        api.get(`/users/oauth/${provider}/start/`, {
            params: { next }
        }),
};

// ---------------------------------------------------------------------------
// Two-factor authentication (TOTP)
// ---------------------------------------------------------------------------

export const mfaAPI = {
    getStatus:             ()     => api.get('/users/mfa/status/'),
    setup:                 ()     => api.post('/users/mfa/setup/'),
    confirm:               (code) => api.post('/users/mfa/confirm/', { code }),
    disable:               (code) => api.post('/users/mfa/disable/', { code }),
    regenerateBackupCodes: (code) => api.post('/users/mfa/backup-codes/', { code }),

    // Pre-login enrollment for roles that must have 2FA (Admin/Triager). The
    // signed enrollment token from the login response is the only credential.
    enrollSetup:           (token)       => api.post('/users/mfa/enroll/setup/', { enrollment_token: token }),
    enrollConfirm:         (token, code) => api.post('/users/mfa/enroll/confirm/', { enrollment_token: token, code }),
};

// ---------------------------------------------------------------------------
// Company
// ---------------------------------------------------------------------------

export const companyAPI = {
    // Company profile
    createCompanyProfile: (data) => api.post('/users/companies/', data),
    getProfile:           ()     => api.get('/users/companies/my_profile/'),
    updateProfile:        (id, data) => api.put(`/users/companies/${id}/`, data),
    hasCompanyProfile:    ()     => api.get('/users/companies/has_profile/'),

    // Programs
    createProgram:        (data) => api.post('/programs/programs/', data),
    getPrograms:          ()     => api.get('/programs/company/'),
    getDashboard:         ()     => api.get('/programs/dashboard/'),
    getProgramDashboard:  (id)   => api.get(`/programs/${id}/dashboard/`),
    activateProgram:      (id)   => api.post(`/programs/programs/${id}/activate/`),
    pauseProgram:         (id)   => api.post(`/programs/programs/${id}/pause/`),
    closeProgram:         (id)   => api.post(`/programs/programs/${id}/close/`),

    // Scopes
    createScope:          (programId, data) => api.post(`/programs/${programId}/scopes/`, data),
    updateScope:          (programId, scopeId, data) => api.patch(`/programs/${programId}/scopes/${scopeId}/`, data),
    deleteScope:          (programId, scopeId) => api.delete(`/programs/${programId}/scopes/${scopeId}/`),

    // Invitations
    sendInvitation:       (programId, data) => api.post(`/programs/${programId}/invitations/`, data),
    getInvitations:       (programId) => api.get(`/programs/${programId}/invitations/`),
    revokeInvitation:     (programId, invId) => api.post(`/programs/${programId}/invitations/${invId}/revoke/`),

    // Applications
    getApplications:      (programId) => api.get(`/programs/${programId}/applications/`),
    approveApplication:   (programId, appId, data) => api.post(`/programs/${programId}/applications/${appId}/approve/`, data),
    rejectApplication:    (programId, appId, data) => api.post(`/programs/${programId}/applications/${appId}/reject/`, data),
};

// ---------------------------------------------------------------------------
// Researcher
// ---------------------------------------------------------------------------

export const researcherAPI = {
    // Profile
    createProfile:        (data) => api.post('/users/researchers/', data),
    getProfile:           ()     => api.get('/users/researchers/my_profile/'),
    updateProfile:        (id, data) => api.put(`/users/researchers/${id}/`, data),

    // Programs
    getPrograms:          (params = {}) => api.get('/programs/researcher/', { params }),
    getProgram:           (id)   => api.get(`/programs/programs/${id}/`),
    joinProgram:          (id, data = {}) => api.post(`/programs/programs/${id}/join/`, data),

    // Favorites
    getFavorites:         ()     => api.get('/programs/favorites/'),
    addFavorite:          (data) => api.post('/programs/favorites/', data),
    removeFavorite:       (id)   => api.delete(`/programs/favorites/${id}/`),

    // Invitations
    getInvitations:       ()     => api.get('/programs/programs/invitations/'),
    acceptInvitation:     (programId, invId) => api.post(`/programs/programs/${programId}/invitations/${invId}/accept/`),
    rejectInvitation:     (programId, invId) => api.post(`/programs/programs/${programId}/invitations/${invId}/reject/`),

    // Applications
    getApplications:      ()     => api.get('/programs/programs/applications/'),
    withdrawApplication:  (programId, appId) => api.post(`/programs/programs/${programId}/applications/${appId}/withdraw/`),
};

// ---------------------------------------------------------------------------
// Reports
// ---------------------------------------------------------------------------

export const reportAPI = {
    // CRUD
    getReports:           (params = {}) => api.get('/reports/', { params }),
    getReport:            (id)   => api.get(`/reports/${id}/`),
    createReport:         (data) => api.post('/reports/', data),
    updateReport:         (id, data) => api.patch(`/reports/${id}/`, data),
    deleteReport:         (id)   => api.delete(`/reports/${id}/`),

    // Status transitions
    submitForReview:      (id)   => api.post(`/reports/${id}/submit_for_review/`),
    acceptReport:         (id, data) => api.post(`/reports/${id}/accept/`, data),
    rejectReport:         (id, data) => api.post(`/reports/${id}/reject/`, data),
    reopenReport:         (id)   => api.post(`/reports/${id}/reopen/`),
    changeStatus:         (id, data) => api.patch(`/reports/${id}/change_status/`, data),

    // Triage
    assignToMe:           (id)   => api.post(`/reports/${id}/assign_to_me/`),
    getTriageDashboard:   ()     => api.get('/reports/triage_dashboard/'),

    // Comments & activity
    getComments:          (id)   => api.get(`/reports/${id}/comments/`),
    addComment:           (id, data) => api.post(`/reports/${id}/comments/`, data),
    editComment:          (id, commentId, data) => api.patch(`/reports/${id}/comments/${commentId}/`, data),
    deleteComment:        (id, commentId) => api.delete(`/reports/${id}/comments/${commentId}/`),
    getActivityLogs:      (id)   => api.get(`/reports/${id}/activity_logs/`),

    // Attachments
    getAttachments:       (id)   => api.get(`/reports/${id}/attachments/`),
    uploadAttachment:     (id, data) => api.post(`/reports/${id}/upload_attachment/`, data, {
        headers: { 'Content-Type': 'multipart/form-data' },
    }),
    downloadAttachment:   (id, attId) => api.get(`/reports/${id}/download/${attId}/`, {
        responseType: 'blob',
    }),

    // Researcher views
    getMySubmissions:     (params = {}) => api.get('/reports/my_submissions/', { params }),
    getStats:             ()     => api.get('/reports/stats/'),
};

export const walletAPI = {
    getWallet:       () => api.get('/wallet/'),
    getTransactions: (params) => api.get('/wallet/transactions/', { params }),
};

export const leaderboardAPI = {
    getLeaderboard: (params) => api.get('/leaderboard/', { params }),
    getMe: (params) => api.get('/leaderboard/me/', { params }),
};

// ---------------------------------------------------------------------------
// Notifications
// ---------------------------------------------------------------------------

export const notificationAPI = {
    getAll:               ()     => api.get('/programs/notifications/'),
    getUnreadCount:       ()     => api.get('/programs/notifications/unread_count/'),
    markRead:             (id)   => api.post(`/programs/notifications/${id}/mark_read/`),
    markAllRead:          ()     => api.post('/programs/notifications/mark_all_read/'),
};

// ---------------------------------------------------------------------------
// Public / Home
// ---------------------------------------------------------------------------

export const homeAPI = {
    getStats:             ()     => api.get('/home/stats/'),
    getPublicReports:     ()     => api.get('/home/public-reports/'),
    getPublicPrograms:    (params = {}) => api.get('/programs/programs/public/', { params }),
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

export const isAuthenticated = () => !!localStorage.getItem('access_token');

export const getAuthHeaders = () => {
    const token = localStorage.getItem('access_token');
    return token ? { Authorization: `Bearer ${token}` } : {};
};

export default api;