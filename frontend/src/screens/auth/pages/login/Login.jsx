import {Link, useLocation, useNavigate} from "react-router-dom";
import "bootstrap/dist/css/bootstrap.min.css";
import "../../../../styles/Login.css";
import API from "../../../../api";
import React, {useState} from "react";
import {Alert} from 'react-bootstrap';
import CaptchaField from "../../components/CaptchaField";

function Login() {
    const location = useLocation();
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");
    const navigate = useNavigate();
    const [captchaToken, setCaptchaToken] = useState(null);

    const validatePassword = (password) => {
        const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{6,}$/;
        return passwordRegex.test(password);
    };

    const handleSubmit = async (event) => {
        event.preventDefault();
        setError("");
        setSuccess("");

        if (!username || !password || !validatePassword(password)) {
            setError("Неверные имя пользователя или пароль.");
            return;
        }

        try {
            const response = await API.post("/auth/login-2fa", {
                username: username,
                password: password,
                captcha: captchaToken
            });

            if (response.status === 200) {
                setSuccess("Вход успешен! Перенаправление...");
                const from = location.state?.from || '/';

                setTimeout(() => navigate("/2fa", {
                    state: {username, password, from }
                }), 1500);

            }
        } catch (error) {
            console.error("Ошибка запроса:", error);
            if (error.response?.status === 400) {
                setError("Неверный код 2FA.");
            } else if (error.response?.status === 401) {
                setError("Неверные имя пользователя или пароль.");
            } else {
                setError("Ошибка входа. Попробуйте позже.");
            }
        }
    };

    return (
        <div className="login-container d-flex align-items-center justify-content-center">
            <div className="login-box p-5 rounded shadow">
                <h2 className="text-center mb-4 text-primary">Вход</h2>
                {error && <Alert variant="danger">{error}</Alert>}
                {success && <Alert variant="success">{success}</Alert>}

                <form onSubmit={handleSubmit}>
                    <div className="mb-3">
                        <label className="form-label">Имя пользователя</label>
                        <input type="text"
                               className="form-control"
                               placeholder="Введите имя пользователя"
                               value={username}
                               onChange={(e) => setUsername(e.target.value)}
                        />
                    </div>

                    <div className="mb-3">
                        <label className="form-label">Пароль</label>
                        <input type="password"
                               className="form-control"
                               placeholder="Введите пароль"
                               value={password}
                               onChange={(e) => setPassword(e.target.value)}
                        />
                    </div>
                    <CaptchaField onChange={(token) => setCaptchaToken(token)} />
                    <button type="submit" className="btn btn-primary w-100" disabled={!captchaToken}>
                        Войти
                    </button>
                </form>

                <div className="text-center mt-3">
                    <p>
                        Нет аккаунта? <Link to="/register" className="text-decoration-none">Зарегистрируйтесь</Link>
                    </p>
                </div>

                <div className="mt-3">
                    <button
                        className="btn btn-outline-danger w-100 mb-2"
                        onClick={() => window.location.href = "https://localhost:8000/api/auth/google/"}
                    >
                        Войти через Google
                    </button>
                </div>

            </div>
        </div>
    );
}

export default Login;
