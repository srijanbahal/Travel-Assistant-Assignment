"""
Local Recommendations Service
Provides attractions, restaurants, and cultural tips for destinations.
"""
from typing import List, Optional
from langchain_core.tools import tool

# Mock data for recommendations (would be DB-backed in production)
ATTRACTIONS = {
    "delhi": [
        {"name": "Red Fort", "type": "Historical Monument", "rating": 4.6, "description": "UNESCO World Heritage Site, Mughal-era fort"},
        {"name": "India Gate", "type": "Memorial", "rating": 4.7, "description": "War memorial and iconic landmark"},
        {"name": "Qutub Minar", "type": "Historical Monument", "rating": 4.5, "description": "73-meter tall minaret from 12th century"},
        {"name": "Lotus Temple", "type": "Religious Site", "rating": 4.6, "description": "Bahá'í House of Worship with lotus-shaped architecture"},
        {"name": "Humayun's Tomb", "type": "Historical Monument", "rating": 4.7, "description": "Mughal emperor's tomb, UNESCO site"}
    ],
    "mumbai": [
        {"name": "Gateway of India", "type": "Monument", "rating": 4.6, "description": "Iconic arch monument overlooking Arabian Sea"},
        {"name": "Marine Drive", "type": "Promenade", "rating": 4.7, "description": "3.6km coastal boulevard, Queen's Necklace at night"},
        {"name": "Elephanta Caves", "type": "Historical Site", "rating": 4.5, "description": "UNESCO site with ancient cave temples"},
        {"name": "Siddhivinayak Temple", "type": "Religious Site", "rating": 4.7, "description": "Famous Ganesha temple"},
        {"name": "Juhu Beach", "type": "Beach", "rating": 4.2, "description": "Popular beach with street food"}
    ],
    "goa": [
        {"name": "Basilica of Bom Jesus", "type": "Church", "rating": 4.7, "description": "UNESCO site with St. Francis Xavier's remains"},
        {"name": "Aguada Fort", "type": "Historical Monument", "rating": 4.5, "description": "17th century Portuguese fort with lighthouse"},
        {"name": "Dudhsagar Falls", "type": "Natural Wonder", "rating": 4.6, "description": "Four-tiered waterfall, 310m high"},
        {"name": "Calangute Beach", "type": "Beach", "rating": 4.3, "description": "Queen of Beaches with water sports"},
        {"name": "Old Goa Churches", "type": "Historical Site", "rating": 4.6, "description": "Collection of Portuguese colonial churches"}
    ],
    "jaipur": [
        {"name": "Amber Fort", "type": "Fort", "rating": 4.7, "description": "Majestic hilltop fort with stunning architecture"},
        {"name": "Hawa Mahal", "type": "Palace", "rating": 4.5, "description": "Palace of Winds with 953 small windows"},
        {"name": "City Palace", "type": "Palace", "rating": 4.6, "description": "Royal residence with museums"},
        {"name": "Jantar Mantar", "type": "Observatory", "rating": 4.4, "description": "UNESCO site with astronomical instruments"},
        {"name": "Nahargarh Fort", "type": "Fort", "rating": 4.5, "description": "Fort with panoramic city views"}
    ],
    "bangalore": [
        {"name": "Lalbagh Botanical Garden", "type": "Garden", "rating": 4.6, "description": "240-acre garden with rare plants"},
        {"name": "Bangalore Palace", "type": "Palace", "rating": 4.4, "description": "Tudor-style palace from 1887"},
        {"name": "Cubbon Park", "type": "Park", "rating": 4.5, "description": "300-acre green space in city center"},
        {"name": "ISKCON Temple", "type": "Religious Site", "rating": 4.7, "description": "Beautiful Krishna temple"},
        {"name": "Wonderla", "type": "Amusement Park", "rating": 4.5, "description": "Popular theme park with rides"}
    ]
}

RESTAURANTS = {
    "delhi": [
        {"name": "Indian Accent", "cuisine": "Modern Indian", "price_range": "₹₹₹₹", "rating": 4.8},
        {"name": "Karim's", "cuisine": "Mughlai", "price_range": "₹₹", "rating": 4.5},
        {"name": "Bukhara", "cuisine": "North Indian", "price_range": "₹₹₹₹", "rating": 4.7},
        {"name": "Paranthe Wali Gali", "cuisine": "Street Food", "price_range": "₹", "rating": 4.3},
        {"name": "Saravana Bhavan", "cuisine": "South Indian", "price_range": "₹₹", "rating": 4.4}
    ],
    "mumbai": [
        {"name": "Leopold Cafe", "cuisine": "Continental", "price_range": "₹₹", "rating": 4.3},
        {"name": "Trishna", "cuisine": "Seafood", "price_range": "₹₹₹", "rating": 4.6},
        {"name": "Britannia & Co", "cuisine": "Parsi", "price_range": "₹₹", "rating": 4.5},
        {"name": "Bademiya", "cuisine": "Kebabs", "price_range": "₹₹", "rating": 4.4},
        {"name": "Cafe Mondegar", "cuisine": "Multi-cuisine", "price_range": "₹₹", "rating": 4.2}
    ],
    "goa": [
        {"name": "Gunpowder", "cuisine": "South Indian", "price_range": "₹₹", "rating": 4.5},
        {"name": "Thalassa", "cuisine": "Greek", "price_range": "₹₹₹", "rating": 4.6},
        {"name": "Fisherman's Wharf", "cuisine": "Goan Seafood", "price_range": "₹₹₹", "rating": 4.4},
        {"name": "Curlies", "cuisine": "Beach Shack", "price_range": "₹₹", "rating": 4.2},
        {"name": "Britto's", "cuisine": "Multi-cuisine", "price_range": "₹₹", "rating": 4.3}
    ],
    "jaipur": [
        {"name": "Suvarna Mahal", "cuisine": "Royal Indian", "price_range": "₹₹₹₹", "rating": 4.7},
        {"name": "Laxmi Misthan Bhandar", "cuisine": "Sweets & Snacks", "price_range": "₹", "rating": 4.5},
        {"name": "Handi Restaurant", "cuisine": "Rajasthani", "price_range": "₹₹", "rating": 4.4},
        {"name": "Peacock Rooftop", "cuisine": "Multi-cuisine", "price_range": "₹₹", "rating": 4.3},
        {"name": "1135 AD", "cuisine": "Royal Rajasthani", "price_range": "₹₹₹₹", "rating": 4.6}
    ]
}

CULTURAL_TIPS = {
    "delhi": [
        "Dress modestly when visiting religious sites",
        "Bargain at local markets like Chandni Chowk",
        "Try street food but stick to busy stalls",
        "Use Metro for convenient transport",
        "Book monuments online to skip queues"
    ],
    "mumbai": [
        "Local trains are fastest during rush hours",
        "Try vada pav - Mumbai's iconic street food",
        "Visit Marine Drive at sunset",
        "Auto-rickshaws not allowed in South Mumbai",
        "Carry umbrella during monsoon (Jun-Sep)"
    ],
    "goa": [
        "Rent a scooter for flexibility",
        "Beaches in North are lively, South are peaceful",
        "Try Goan fish curry and feni",
        "Respect the siesta culture (2-4 PM)",
        "Many places closed on Sundays"
    ],
    "jaipur": [
        "Buy a composite ticket for all monuments",
        "Wear comfortable shoes for forts",
        "Try authentic Rajasthani thali",
        "Best to visit October to March",
        "Respect elephant welfare - choose ethical tourism"
    ]
}

@tool
def get_attractions(location: str) -> List[dict]:
    """
    Get popular tourist attractions and things to do in a location.
    Returns list of attractions with name, type, rating, and description.
    """
    normalized = location.lower().strip()
    
    # Check for partial matches
    attractions = None
    for city, data in ATTRACTIONS.items():
        if city in normalized or normalized in city:
            attractions = data
            break
    
    if not attractions:
        return [{"message": f"No attraction data available for {location}. Try major cities like Delhi, Mumbai, Goa, Jaipur, or Bangalore."}]
    
    return attractions

@tool
def get_restaurants(location: str, cuisine: Optional[str] = None) -> List[dict]:
    """
    Get restaurant recommendations in a location.
    Optionally filter by cuisine type.
    """
    normalized = location.lower().strip()
    
    restaurants = None
    for city, data in RESTAURANTS.items():
        if city in normalized or normalized in city:
            restaurants = data
            break
    
    if not restaurants:
        return [{"message": f"No restaurant data for {location}. Try Delhi, Mumbai, Goa, or Jaipur."}]
    
    if cuisine:
        filtered = [r for r in restaurants if cuisine.lower() in r["cuisine"].lower()]
        return filtered if filtered else restaurants
    
    return restaurants

@tool  
def get_cultural_tips(location: str) -> List[str]:
    """
    Get cultural tips and local advice for visiting a location.
    Helps travelers understand local customs and practical tips.
    """
    normalized = location.lower().strip()
    
    tips = None
    for city, data in CULTURAL_TIPS.items():
        if city in normalized or normalized in city:
            tips = data
            break
    
    if not tips:
        return [f"No specific tips for {location}. General advice: respect local customs, stay hydrated, and keep valuables safe."]
    
    return tips
