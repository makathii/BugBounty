import React from 'react';
import { useNavigate } from 'react-router-dom';
import ProgramWizard from '../../components/company/ProgramWizard';

const CreateProgram = () => {
    const navigate = useNavigate();

    return (
        <div style={{ padding: '2rem' }}>
            <ProgramWizard
                onSuccess={(program) => {
                    navigate('/company/programs');
                }}
                onCancel={() => navigate('/company/programs')}
            />
        </div>
    );
};

export default CreateProgram;