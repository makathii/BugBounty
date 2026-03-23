import React from 'react';
import ReportForm from '../../components/reports/ReportForm';
import { useNavigate, useSearchParams } from 'react-router-dom';

const SubmitReport = () => {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const programId = searchParams.get('program');

    const handleSuccess = () => {
        alert('Report submitted successfully!');
        navigate('/reports');
    };

    const handleCancel = () => {
        navigate('/dashboard');
    };

    return (
        <div style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto' }}>
            <ReportForm onSuccess={handleSuccess} onCancel={handleCancel} programId={programId} />
        </div>
    );
};

export default SubmitReport;