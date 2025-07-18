"""
Future Phase: Marketplace API for strategy/plugin store
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

from utils.logging_config import get_logger

logger = get_logger("marketplace")


class StrategyType(str, Enum):
    """Strategy types in marketplace"""
    SIGNAL_PROVIDER = "signal_provider"
    INDICATOR = "indicator"
    EXPERT_ADVISOR = "expert_advisor"
    SCRIPT = "script"
    TEMPLATE = "template"


class StrategyStatus(str, Enum):
    """Strategy status in marketplace"""
    ACTIVE = "active"
    PENDING = "pending"
    SUSPENDED = "suspended"
    DEPRECATED = "deprecated"


class Strategy(BaseModel):
    """Marketplace strategy model"""
    id: str
    name: str
    description: str
    type: StrategyType
    status: StrategyStatus
    author: str
    version: str
    price: float = Field(ge=0)
    currency: str = "USD"
    rating: float = Field(ge=0, le=5)
    downloads: int = Field(ge=0)
    tags: List[str] = []
    requirements: List[str] = []
    compatibility: List[str] = []
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class StrategyReview(BaseModel):
    """Strategy review model"""
    id: str
    strategy_id: str
    user_id: str
    rating: int = Field(ge=1, le=5)
    comment: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class MarketplaceStats(BaseModel):
    """Marketplace statistics"""
    total_strategies: int
    total_downloads: int
    total_revenue: float
    active_strategies: int
    pending_strategies: int
    top_categories: List[Dict[str, Any]]
    recent_releases: List[Strategy]


class MarketplaceService:
    """Marketplace service for strategy/plugin management"""
    
    def __init__(self):
        self.strategies: Dict[str, Strategy] = {}
        self.reviews: Dict[str, List[StrategyReview]] = {}
        self.user_purchases: Dict[str, List[str]] = {}
    
    async def get_strategies(self, 
                           strategy_type: Optional[StrategyType] = None,
                           status: Optional[StrategyStatus] = None,
                           search: Optional[str] = None,
                           limit: int = 50,
                           offset: int = 0) -> List[Strategy]:
        """Get strategies from marketplace"""
        try:
            # In production, this would query from database
            strategies = list(self.strategies.values())
            
            # Apply filters
            if strategy_type:
                strategies = [s for s in strategies if s.type == strategy_type]
            
            if status:
                strategies = [s for s in strategies if s.status == status]
            
            if search:
                search_lower = search.lower()
                strategies = [s for s in strategies 
                            if search_lower in s.name.lower() or 
                               search_lower in s.description.lower()]
            
            # Apply pagination
            total = len(strategies)
            strategies = strategies[offset:offset + limit]
            
            logger.info(f"Retrieved {len(strategies)} strategies from marketplace")
            return strategies
            
        except Exception as e:
            logger.error(f"Error getting strategies: {e}")
            return []
    
    async def get_strategy(self, strategy_id: str) -> Optional[Strategy]:
        """Get specific strategy"""
        try:
            strategy = self.strategies.get(strategy_id)
            if strategy:
                logger.info(f"Retrieved strategy: {strategy_id}")
                return strategy
            else:
                logger.warning(f"Strategy not found: {strategy_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting strategy {strategy_id}: {e}")
            return None
    
    async def create_strategy(self, strategy_data: Dict[str, Any], author_id: str) -> Strategy:
        """Create new strategy"""
        try:
            strategy = Strategy(
                id=f"strategy_{len(self.strategies) + 1}",
                name=strategy_data["name"],
                description=strategy_data["description"],
                type=StrategyType(strategy_data["type"]),
                status=StrategyStatus.PENDING,
                author=author_id,
                version=strategy_data.get("version", "1.0.0"),
                price=strategy_data.get("price", 0.0),
                currency=strategy_data.get("currency", "USD"),
                rating=0.0,
                downloads=0,
                tags=strategy_data.get("tags", []),
                requirements=strategy_data.get("requirements", []),
                compatibility=strategy_data.get("compatibility", []),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            self.strategies[strategy.id] = strategy
            logger.info(f"Created strategy: {strategy.id}")
            
            return strategy
            
        except Exception as e:
            logger.error(f"Error creating strategy: {e}")
            raise
    
    async def update_strategy(self, strategy_id: str, 
                            update_data: Dict[str, Any]) -> Optional[Strategy]:
        """Update existing strategy"""
        try:
            strategy = self.strategies.get(strategy_id)
            if not strategy:
                return None
            
            # Update fields
            for field, value in update_data.items():
                if hasattr(strategy, field):
                    setattr(strategy, field, value)
            
            strategy.updated_at = datetime.utcnow()
            
            logger.info(f"Updated strategy: {strategy_id}")
            return strategy
            
        except Exception as e:
            logger.error(f"Error updating strategy {strategy_id}: {e}")
            raise
    
    async def delete_strategy(self, strategy_id: str) -> bool:
        """Delete strategy"""
        try:
            if strategy_id in self.strategies:
                del self.strategies[strategy_id]
                # Also remove reviews
                if strategy_id in self.reviews:
                    del self.reviews[strategy_id]
                
                logger.info(f"Deleted strategy: {strategy_id}")
                return True
            else:
                logger.warning(f"Strategy not found for deletion: {strategy_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting strategy {strategy_id}: {e}")
            return False
    
    async def purchase_strategy(self, strategy_id: str, user_id: str) -> bool:
        """Purchase strategy"""
        try:
            strategy = self.strategies.get(strategy_id)
            if not strategy:
                return False
            
            # Check if already purchased
            user_purchases = self.user_purchases.get(user_id, [])
            if strategy_id in user_purchases:
                return True  # Already purchased
            
            # Add to user purchases
            if user_id not in self.user_purchases:
                self.user_purchases[user_id] = []
            
            self.user_purchases[user_id].append(strategy_id)
            
            # Update download count
            strategy.downloads += 1
            
            logger.info(f"User {user_id} purchased strategy {strategy_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error purchasing strategy {strategy_id}: {e}")
            return False
    
    async def get_user_purchases(self, user_id: str) -> List[Strategy]:
        """Get user's purchased strategies"""
        try:
            purchased_ids = self.user_purchases.get(user_id, [])
            purchases = []
            
            for strategy_id in purchased_ids:
                strategy = self.strategies.get(strategy_id)
                if strategy:
                    purchases.append(strategy)
            
            logger.info(f"Retrieved {len(purchases)} purchases for user {user_id}")
            return purchases
            
        except Exception as e:
            logger.error(f"Error getting purchases for user {user_id}: {e}")
            return []
    
    async def add_review(self, strategy_id: str, user_id: str, 
                        rating: int, comment: str) -> StrategyReview:
        """Add strategy review"""
        try:
            review = StrategyReview(
                id=f"review_{len(self.reviews.get(strategy_id, [])) + 1}",
                strategy_id=strategy_id,
                user_id=user_id,
                rating=rating,
                comment=comment,
                created_at=datetime.utcnow()
            )
            
            if strategy_id not in self.reviews:
                self.reviews[strategy_id] = []
            
            self.reviews[strategy_id].append(review)
            
            # Update strategy rating
            await self._update_strategy_rating(strategy_id)
            
            logger.info(f"Added review for strategy {strategy_id}")
            return review
            
        except Exception as e:
            logger.error(f"Error adding review: {e}")
            raise
    
    async def get_reviews(self, strategy_id: str) -> List[StrategyReview]:
        """Get strategy reviews"""
        try:
            reviews = self.reviews.get(strategy_id, [])
            logger.info(f"Retrieved {len(reviews)} reviews for strategy {strategy_id}")
            return reviews
            
        except Exception as e:
            logger.error(f"Error getting reviews for strategy {strategy_id}: {e}")
            return []
    
    async def get_marketplace_stats(self) -> MarketplaceStats:
        """Get marketplace statistics"""
        try:
            strategies = list(self.strategies.values())
            
            total_strategies = len(strategies)
            total_downloads = sum(s.downloads for s in strategies)
            total_revenue = sum(s.price * s.downloads for s in strategies)
            active_strategies = len([s for s in strategies if s.status == StrategyStatus.ACTIVE])
            pending_strategies = len([s for s in strategies if s.status == StrategyStatus.PENDING])
            
            # Top categories
            category_counts = {}
            for strategy in strategies:
                category = strategy.type.value
                category_counts[category] = category_counts.get(category, 0) + 1
            
            top_categories = [
                {"category": cat, "count": count}
                for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
            ]
            
            # Recent releases (last 10)
            recent_releases = sorted(strategies, key=lambda s: s.created_at, reverse=True)[:10]
            
            stats = MarketplaceStats(
                total_strategies=total_strategies,
                total_downloads=total_downloads,
                total_revenue=total_revenue,
                active_strategies=active_strategies,
                pending_strategies=pending_strategies,
                top_categories=top_categories,
                recent_releases=recent_releases
            )
            
            logger.info("Generated marketplace statistics")
            return stats
            
        except Exception as e:
            logger.error(f"Error getting marketplace stats: {e}")
            raise
    
    async def _update_strategy_rating(self, strategy_id: str):
        """Update strategy rating based on reviews"""
        try:
            strategy = self.strategies.get(strategy_id)
            reviews = self.reviews.get(strategy_id, [])
            
            if strategy and reviews:
                total_rating = sum(r.rating for r in reviews)
                average_rating = total_rating / len(reviews)
                strategy.rating = round(average_rating, 1)
                
                logger.debug(f"Updated rating for strategy {strategy_id}: {strategy.rating}")
                
        except Exception as e:
            logger.error(f"Error updating strategy rating: {e}")


# Global marketplace service instance
_marketplace_service = None


def get_marketplace_service() -> MarketplaceService:
    """Get global marketplace service instance"""
    global _marketplace_service
    if _marketplace_service is None:
        _marketplace_service = MarketplaceService()
    return _marketplace_service