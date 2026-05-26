// src/components/auth/Login.jsx
import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import './auth.css';
import { FaGithub, FaGoogle, FaGitlab } from 'react-icons/fa';

const Login = () => {
    const navigate = useNavigate();
    const { login, loginWithOAuth } = useAuth();
    const [formData, setFormData] = useState({
        username: '',
        password: ''
    });

    const [errors, setErrors] = useState({});
    const [isLoading, setIsLoading] = useState(false);

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value
        });
        if (errors[e.target.name]) {
            setErrors({
                ...errors,
                [e.target.name]: ''
            });
        }
        if (errors.general) {
            setErrors({ ...errors, general: '' });
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setErrors({});
        setIsLoading(true);

        try {
            const result = await login(formData.username, formData.password);

            if (result.success) {
                navigate('/dashboard');
            } else {
                setErrors({ general: result.error || 'Login failed' });
            }
        } catch (err) {
            setErrors({ general: 'An unexpected error occurred' });
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="auth-container">
            <div className="login-container">
                <div className="auth-header">
                    <h2>Welcome Back</h2>
                    <p>Sign in to your Bug Bounty account</p>
                </div>

                {errors.general && (
                    <div className="error-message">{errors.general}</div>
                )}

                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label htmlFor="username">Username</label>
                        <input
                            type="text"
                            id="username"
                            name="username"
                            placeholder="Enter your username"
                            value={formData.username}
                            onChange={handleChange}
                            required
                            className={errors.username ? 'error' : ''}
                            disabled={isLoading}
                        />
                        {errors.username && <span className="error-text">{errors.username}</span>}
                    </div>

                    <div className="form-group">
                        <label htmlFor="password">Password</label>
                        <input
                            type="password"
                            id="password"
                            name="password"
                            placeholder="Enter your password"
                            value={formData.password}
                            onChange={handleChange}
                            required
                            className={errors.password ? 'error' : ''}
                            disabled={isLoading}
                        />
                        {errors.password && <span className="error-text">{errors.password}</span>}
                    </div>

                    <button
                        type="submit"
                        disabled={isLoading}
                        className="submit-btn"
                    >
                        {isLoading && <span className="loading-spinner"></span>}
                        {isLoading ? 'Signing in...' : 'Sign In'}
                    </button>
                </form>

                <div className="auth-divider">
                    <span>or continue with</span>
                </div>

                <div className="oauth-buttons">
                    <button
                        type="button"
                        className="oauth-btn github"
                        onClick={() => loginWithOAuth('github')}
                        disabled={isLoading}
                    >
                        <FaGithub className="btn-icon" size={24} />
                    </button>

                    <button
                        type="button"
                        className="oauth-btn google"
                        onClick={() => loginWithOAuth('google')}
                        disabled={isLoading}
                    >
                        <FaGoogle className="btn-icon" size={24} />
                    </button>

                    <button
                        type="button"
                        className="oauth-btn gitlab"
                        onClick={() => loginWithOAuth('gitlab')}
                        disabled={isLoading}
                    >
                        <FaGitlab className="btn-icon" size={24} />
                    </button>
                </div>

                <p className="switch-auth">
                    Don't have an account?{' '}
                    <Link to="/register" className="link-btn">
                        Create one here
                    </Link>
                </p>
            </div>
        </div>
    );
};

export default Login;