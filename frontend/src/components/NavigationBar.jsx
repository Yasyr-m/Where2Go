import React, {useEffect, useState} from "react";
import {Navbar, Nav, Container, Button, Modal, Form, Alert} from "react-bootstrap";
import icon from "../assets/icon.png";
import API from "../api";
import {useNavigate} from "react-router-dom";

const NavigationBar = ({user}) => {
    const [showSettings, setShowSettings] = React.useState(false);
    const [oldPassword, setOldPassword] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");
    const navigate = useNavigate();
    const [newUsername, setNewUsername] = useState(user.username.toString());

    useEffect(() => {
        if (error || success) {
            const timer = setTimeout(() => {
                setError("");
                setSuccess("");
            }, 5000); // 5 секунд

            return () => clearTimeout(timer);
        }
    }, [error, success]);

    const showError = (msg) => {
        setSuccess("");
        setError(msg);
    }

    const showSuccess = (msg) => {
        setError("");
        setSuccess(msg);
    }

    const handleUsernameChange = async () => {
        if (newUsername === user.username) {
            showError("Новое имя пользователя совпадает с текущим.");
            return;
        }
        try {
            const response = await API.post("/users/update/", {
                username: user.username,
                newUsername: newUsername
            });
            if (response.status === 200) {
                showSuccess("Имя пользователя успешно изменено.");
                user.username = newUsername;
                setNewUsername(newUsername);
            } else {
                showError(`Ошибка при смене имени пользователя: ${response.data.error}`);
            }
        } catch (err) {
            showError(`Ошибка при смене имени пользователя: ${err.response?.data?.error || err.message}`);
        }
    }

    const handlePasswordChange = async () => {
        try {
            const response = await API.post("/users/update/", {
                username: user.username,
                old_password: oldPassword,
                password: newPassword
            });
            if (response.status === 200) {
                showSuccess("Пароль успешно изменён.");
                setOldPassword('');
                setNewPassword('');
            } else {
                showError(`Ошибка при смене пароля: ${response.data.error}`);
            }
        } catch (err) {
            showError(`Ошибка при смене пароля: ${err.response?.data?.error || err.message}`);
        }
    }

    const handleDeactivateSessions = async () => {
        try {
            const response = await API.delete("/sessions/");
            if (response.status === 204) {
                showSuccess("Все сессии завершены.")
            }
            else {
                showError(`Ошибка при завершении сессий: ${response.data.error}`);
            }
        } catch (err) {
            showError("Ошибка при деактивации сессий");
        }
    };

    const handleLogout = () => {
        console.log("Выход из аккаунта...");
        localStorage.removeItem("token");
        setTimeout(() => navigate("/login"), 1500);
    };

    return (
        <>
            <Navbar style={{backgroundColor: "#79afe8"}} expand="lg">
                <Container>
                    <Navbar.Brand href="\profile">
                        <img
                            src={icon}
                            alt="Logo"
                            width="20"
                            height="25"
                            className="d-inline-block align-text-top"
                        />
                        {' '}Where2Go
                    </Navbar.Brand>
                    <Nav className="me-auto">
                        <Nav.Link disabled>{user.username}</Nav.Link>
                        <Nav.Link disabled>{user.email}</Nav.Link>
                    </Nav>
                    <Button variant="outline-dark" onClick={() => setShowSettings(true)}>
                        Настройки
                    </Button>
                    <Button variant="outline-dark" className="ms-2" onClick={handleLogout}>
                        Выйти
                    </Button>
                </Container>
            </Navbar>

            <Modal show={showSettings} onHide={() => setShowSettings(false)}>
                <Modal.Header closeButton>
                    <Modal.Title>Настройки безопасности</Modal.Title>
                </Modal.Header>
                <Modal.Body>
                    {error && <Alert variant="danger">{error}</Alert>}
                    {success && <Alert variant="success">{success}</Alert>}

                    <Form>
                        <Form.Group className="mb-3" controlId="newUsername">
                            <Form.Label>Имя пользователя</Form.Label>
                            <Form.Control
                                type="text"
                                placeholder="Введите новое имя пользователя"
                                value={newUsername}
                                onChange={(e) => setNewUsername(e.target.value)}
                            />
                        </Form.Group>
                        <Button variant="primary" onClick={handleUsernameChange} className="justify-content-center">
                            Сменить имя пользователя
                        </Button>

                        <hr/>

                        <Form.Group className="mb-3 mt-4" controlId="oldPassword">
                            <Form.Label>Текущий пароль</Form.Label>
                            <Form.Control
                                type="password"
                                placeholder="Введите текущий пароль"
                                value={oldPassword}
                                onChange={(e) => setOldPassword(e.target.value)}
                            />
                        </Form.Group>

                        <Form.Group className="mb-3" controlId="newPassword">
                            <Form.Label>Новый пароль</Form.Label>
                            <Form.Control
                                type="password"
                                placeholder="Введите новый пароль"
                                value={newPassword}
                                onChange={(e) => setNewPassword(e.target.value)}
                            />
                        </Form.Group>

                        <Button variant="primary" onClick={handlePasswordChange} className="justify-content-center">
                            Сменить пароль
                        </Button>


                        <hr/>

                        <p className="mt-4">Хотите завершить все сессии (кроме текущей)?</p>
                        <Button variant="danger" onClick={handleDeactivateSessions}>
                            Завершить сеансы
                        </Button>
                    </Form>
                </Modal.Body>
            </Modal>
        </>
    );
};

export default NavigationBar;
