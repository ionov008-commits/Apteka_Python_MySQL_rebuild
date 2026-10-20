namespace WebApplication1.wwwroot.js
{
    public class geo_helper
    {
        async function getCoordsByAddress(address) {
        try {
            const response = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(address)}`);
            const data = await response.json();
            if (data && data.length > 0) {
                return {
                    lat: parseFloat(data[0].lat),
                    lon: parseFloat(data[0].lon)
                };
            }
        } catch (e) {
            console.error("Ошибка геокодинга:", e);
        }
        return null;
    }
    }
}
