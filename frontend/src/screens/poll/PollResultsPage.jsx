import React, {useEffect, useRef, useState} from 'react';
import {useNavigate, useParams} from 'react-router-dom';
import {Spinner, Alert, Container, Form, Button, Modal, InputGroup} from 'react-bootstrap';
import API from "../../api";
import NavigationBar from "../../components/NavigationBar";
import RecommendedPlacesList from "./components/RecommendedPlacesList";
import "../../styles/styles.css";
import {load2GIS} from "../../utils/load2gis";

const PollResultsPage = () => {
    const {pollId} = useParams();
    const navigate = useNavigate();
    const mapRef = useRef(null);
    const mapInstanceRef = useRef(null);
    const markerRef = useRef(null);
    const circleRef = useRef(null);
    const [shareLink, setShareLink] = useState("");
    const [showModal, setShowModal] = useState(false);
    const [shareError, setShareError] = useState(null);
    const [user, setUser] = useState(null);
    const [results, setResults] = useState(null);
    const [recommendedPlaces, setRecommendedPlaces] = useState([]);
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [radius, setRadius] = useState(1000);
    const [minRating, setMinRating] = useState(4.0);

    useEffect(() => {
        const fetchResults = async () => {
            try {
                const userRes = await API.get("/auth/me");
                setUser(userRes.data);

                const response = await API.get(`/polls/${pollId}/results/`);
                setResults(response.data.results);
                setRadius(response.data.results.radius);
                setRecommendedPlaces(response.data.recommended_places);

            } catch (error) {
                setError(error.response?.data?.error || 'Ошибка загрузки результатов');
                setTimeout(() => navigate(`/polls/`), 1500);
            } finally {
                setLoading(false);
            }
        };
        fetchResults().then(r => {
        });
    }, []);

    useEffect(() => {
        if (!results?.average_point || !results?.radius) {
            return;
        }

        const {lat, lon} = results.average_point;
        const radius = results.radius;

        load2GIS().then((DG) => {
            if (window.DG) {
                console.log("DG доступен:", window.DG);
                DG = window.DG;
            } else {
                console.error("DG не найден в window!");
            }

            const interval = setInterval(() => {

                if (mapRef.current && DG && typeof DG.map === "function") {
                    clearInterval(interval);

                    if (mapInstanceRef.current) {
                        mapInstanceRef.current.remove();
                        mapInstanceRef.current = null;
                    }
                    const map = DG.map(mapRef.current, {
                        center: [lat, lon],
                        zoom: 15,
                    });
                    mapInstanceRef.current = map;

                    markerRef.current = DG.marker([lat, lon]).addTo(map);
                    circleRef.current = DG.circle([lat, lon], radius, {
                        color: '#007AFF',
                        fillColor: '#AEDDFF',
                        fillOpacity: 0.3,
                    }).addTo(map);
                }
            }, 100);
        }).catch((err) => {
            console.error("Ошибка загрузки 2GIS:", err);
        });
    }, [results]);

    if (loading || !results) {
        return (
            <div className="d-flex justify-content-center mt-5">
                <Spinner animation="border" role="status">
                    <span className="visually-hidden">Загрузка...</span>
                </Spinner>
            </div>
        );
    }

    const handleShare = async () => {
        try {
            setShareError(null);
            const response = await API.post("/access-links/", {
                content_type: "poll_results",
                content_id: pollId,
                duration_hours: 24,
            });

            const link = `${window.location.origin}/access/${response.data.token}`;
            setShareLink(link);
            setShowModal(true);
        } catch (err) {
            setShareError("Не удалось создать ссылку. Попробуйте позже.");
        }
    };

    const handleRefresh = async (radius, minRating) => {
        try {
            setRefreshing(true);
            const response = await API.get(`/polls/${pollId}/results/`, {
                params: {
                    radius,
                    min_rating: minRating,
                }
            });
            setResults(response.data.results);
            setRadius(response.data.results.radius || 1000);
            setMinRating(response.data.results.min_rating);
            setRecommendedPlaces(response.data.recommended_places);
        } catch (error) {
            setError(error.response?.data?.error || 'Ошибка загрузки результатов');
            setTimeout(() => navigate(`/polls/`), 1500);
        } finally {
            setRefreshing(false);
        }
    }

    if (refreshing) {
        return (
            <div className="custom-bg" style={{color: "#000000", marginBottom: "20px"}}>
                <NavigationBar user={user}/>
                <Spinner animation="border" role="status">
                    <span className="visually-hidden">Загрузка...</span>
                </Spinner>
            </div>
        );
    }

    return (
        <div className="custom-bg" style={{color: "#000000", marginBottom: "20px"}}>
            <NavigationBar user={user}/>
            <Container className="mt-4">
                {error && <Alert variant="danger">{error}</Alert>}
                <h2>Результаты опроса</h2>
                <p>Всего голосов: {results.total_votes}</p>
                <p>Категории с наибольшим количеством голосов: {results.most_popular_categories.join(', ')}</p>
                <p>Точка поиска: {results.average_point.lat}, {results.average_point.lon} </p>
                <Button className="mt-4 me-2" variant="outline-primary" onClick={handleShare}>
                    Поделиться результатами
                </Button>

                {shareError && <Alert variant="danger" className="mt-2">{shareError}</Alert>}

                <Modal show={showModal} onHide={() => setShowModal(false)}>
                    <Modal.Header closeButton>
                        <Modal.Title>Ссылка для доступа</Modal.Title>
                    </Modal.Header>
                    <Modal.Body>
                        <Form.Label>Скопируйте и отправьте ссылку:</Form.Label>
                        <InputGroup className="mb-3">
                            <Form.Control type="text" readOnly value={shareLink}/>
                            <Button variant="secondary" onClick={() => navigator.clipboard.writeText(shareLink)}>Скопировать</Button>
                        </InputGroup>
                    </Modal.Body>
                </Modal>

                <div ref={mapRef} style={{width: "100%", height: "400px", marginTop: "20px"}}/>
                <Form className="mb-3">
                    <Form.Group controlId="radiusInput" className="mt-4">
                        <Form.Label>Радиус поиска (50–2500 м):</Form.Label>
                        <Form.Control
                            type="number"
                            value={radius}
                            min={50}
                            max={2500}
                            disabled={refreshing}
                            onChange={(e) => setRadius(Number(e.target.value))}
                        />
                    </Form.Group>

                    <Form.Group controlId="ratingInput" className="mt-4">
                        <Form.Label>Минимальный рейтинг (0.0–5.0):</Form.Label>
                        <Form.Control
                            type="number"
                            step="0.1"
                            value={minRating}
                            min={0.0}
                            max={5.0}
                            disabled={refreshing}
                            onChange={(e) => setMinRating(Number(e.target.value))}
                        />
                    </Form.Group>

                    <Button className="mt-4" disabled={refreshing}
                            onClick={() => handleRefresh(radius, minRating)}>Обновить</Button>
                </Form>

                {recommendedPlaces.length > 0 && (
                    <RecommendedPlacesList
                        recommendedPlaces={recommendedPlaces}
                        categories={results.most_popular_categories}
                    />)
                }
            </Container>
        </div>
    );
};

export default PollResultsPage;
