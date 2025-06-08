import React, {useEffect, useState} from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {Spinner} from "react-bootstrap";

function OAuthSuccess() {
    const [params] = useSearchParams();
    const navigate = useNavigate();
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const token = params.get("token");

        if (token) {
            localStorage.setItem("token", token);
            setLoading(false);
            setTimeout(() => navigate("/profile"), 1500);
        } else {
            navigate("/login", { state: { error: "Ошибка входа через OAuth" } });
        }
    }, [params, navigate]);

    if (loading) {
        return (
            <div className="d-flex justify-content-center mt-5">
                <Spinner animation="border" role="status">
                    <span className="visually-hidden">Загрузка...</span>
                </Spinner>
            </div>
        );
    }
    return <p>Загрузка...</p>;
}

export default OAuthSuccess;
