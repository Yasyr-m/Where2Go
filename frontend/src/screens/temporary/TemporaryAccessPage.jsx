import React, { useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {Container, Spinner, Alert, Navbar} from "react-bootstrap";
import API from "../../api";
import RecommendedPlacesList from "../poll/components/RecommendedPlacesList";
import "../../styles/styles.css";
import { load2GIS } from "../../utils/load2gis";
import icon from "../../assets/icon.png";

const TemporaryAccessPage = () => {
    const { token } = useParams();
    const navigate = useNavigate();
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [pollData, setPollData] = useState(null);
    const mapRef = useRef(null);
    const mapInstanceRef = useRef(null);
    const markerRef = useRef(null);
    const circleRef = useRef(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const response = await API.get(`/access/${token}/`);
                setPollData(response.data);
            } catch (err) {
                setError(err.response?.data?.error || "Ошибка доступа по ссылке");
                setTimeout(() => navigate("/"), 2500);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    useEffect(() => {
        if (!pollData?.results?.average_point || !pollData?.results?.radius) return;

        const { lat, lon } = pollData.results.average_point;
        const radius = pollData.results.radius;

        load2GIS().then((DG) => {
            if (window.DG) DG = window.DG;

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
                        color: "#007AFF",
                        fillColor: "#AEDDFF",
                        fillOpacity: 0.3,
                    }).addTo(map);
                }
            }, 100);
        });
    }, [pollData]);

    if (loading) {
        return (
            <div className="d-flex justify-content-center mt-5">
                <Spinner animation="border" role="status">
                    <span className="visually-hidden">Загрузка...</span>
                </Spinner>
            </div>
        );
    }

    if (error || !pollData) {
        return (
            <div className="d-flex justify-content-center mt-5">
                <Alert variant="danger">{error}</Alert>
            </div>
        );
    }

    const { results } = pollData;

    return (
        <div className="custom-bg" style={{ color: "#000000", marginBottom: "20px" }}>
            <Navbar style={{backgroundColor: "#79afe8"}} expand="lg">
                <Container>
                    <Navbar.Brand>
                        <img
                            src={icon}
                            alt="Logo"
                            width="20"
                            height="25"
                            className="d-inline-block align-text-top"
                        />
                        {' '}Where2Go
                    </Navbar.Brand>
                </Container>
            </Navbar>
            <Container className="mt-4">
                <h2>Результаты по временной ссылке</h2>
                <p>Владелец опроса: {pollData.owner}</p>
                <p>Всего голосов: {results.total_votes}</p>
                <p>Популярные категории: {results.most_popular_categories.join(", ")}</p>
                <p>Центр поиска: {results.average_point.lat}, {results.average_point.lon}</p>
                <div ref={mapRef} style={{ width: "100%", height: "400px", marginTop: "20px" }} />

                {pollData.recommended_places?.length > 0 && (
                    <RecommendedPlacesList
                        recommendedPlaces={pollData.recommended_places}
                        categories={results.most_popular_categories}
                    />
                )}
            </Container>
        </div>
    );
};

export default TemporaryAccessPage;
