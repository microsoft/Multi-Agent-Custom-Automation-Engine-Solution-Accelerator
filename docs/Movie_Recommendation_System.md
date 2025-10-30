# Movie Recommendation System - Agent Team Configuration

## Overview

The Movie Recommendation Intelligence Team is a specialized multi-agent system designed to provide personalized movie recommendations using advanced AI agents that work collaboratively to understand user preferences and suggest relevant movies.

## Team Composition

### 1. MovieDataAgent
**Specialization**: Movie Database and Information
- **Capabilities**: Access to comprehensive movie catalog, cast/crew information, ratings, reviews, box office data
- **Data Sources**: Movie catalog, film metadata, industry data
- **Use Cases**: Movie details lookup, genre analysis, cast/crew information, release data queries

### 2. UserPreferenceAgent  
**Specialization**: User Behavior and Preferences
- **Capabilities**: User viewing history analysis, preference patterns, rating behavior, demographic insights
- **Data Sources**: User viewing history, preference profiles, rating data
- **Use Cases**: User profiling, viewing pattern analysis, preference identification, behavioral insights

### 3. RecommendationEngineAgent
**Specialization**: Intelligent Recommendation Generation
- **Capabilities**: Advanced recommendation algorithms, collaborative filtering, content-based filtering, personalization
- **Data Sources**: Processed data from other agents (no direct data access)
- **Use Cases**: Personalized recommendations, recommendation explanations, diverse content suggestions

### 4. ProxyAgent
**Specialization**: Coordination and Tool Execution
- **Capabilities**: Tool execution, response formatting, user interaction management
- **Data Sources**: None (coordination only)
- **Use Cases**: User interface coordination, tool execution, response formatting

## Sample Dataset Structure

### Movie Catalog (`movie_catalog.csv`)
- **Fields**: movie_id, title, genre, year, director, rating, runtime_minutes, box_office_millions, imdb_score
- **Purpose**: Comprehensive movie database for content-based recommendations
- **Sample**: Includes popular movies across various genres and time periods

### User Preferences (`user_preferences.csv`)
- **Fields**: user_id, username, age, preferred_genres, favorite_directors, viewing_frequency, subscription_type
- **Purpose**: User demographic and preference profiling
- **Sample**: Diverse user profiles with different viewing habits and preferences

### Viewing History (`user_viewing_history.csv`)
- **Fields**: viewing_id, user_id, movie_id, watch_date, rating, completion_percentage, device_type, watch_time_minutes
- **Purpose**: User behavior tracking and collaborative filtering data
- **Sample**: Actual viewing sessions with ratings and engagement metrics

### Ratings Analysis (`movie_ratings_analysis.csv`)
- **Fields**: movie_id, average_rating, total_reviews, positive_reviews, negative_reviews, trending_score, recommendation_weight
- **Purpose**: Movie popularity and quality metrics for recommendation scoring
- **Sample**: Aggregated rating data with recommendation weights

## Sample Prompts for Testing

### 1. Personal Movie Recommendations
```
I'm looking for movie recommendations. I enjoy sci-fi and thriller genres, particularly movies with complex plots and strong character development. I recently enjoyed Inception, Blade Runner 2049, and The Dark Knight. Can you recommend some movies I might like?
```

**Expected Workflow**:
1. **UserPreferenceAgent** - Analyze user's stated preferences and viewing history
2. **MovieDataAgent** - Gather information about similar movies in sci-fi/thriller genres
3. **RecommendationEngineAgent** - Generate personalized recommendations based on preferences
4. **ProxyAgent** - Format and present the recommendations

### 2. Weekend Movie Night Planning
```
I'm planning a movie night for this weekend with friends. We want something entertaining but not too heavy - maybe a comedy or action movie from the last 5 years. What would you recommend?
```

**Expected Workflow**:
1. **MovieDataAgent** - Search for recent comedy/action movies (2019-2024)
2. **UserPreferenceAgent** - Consider group viewing preferences and popular choices
3. **RecommendationEngineAgent** - Suggest crowd-pleasing options suitable for groups
4. **ProxyAgent** - Present options with reasons why they're good for group viewing

### 3. Viewing Pattern Analysis
```
Can you analyze my viewing patterns and tell me what genres and types of movies I tend to prefer? Also, suggest some movies that might expand my taste to new genres I haven't explored much.
```

**Expected Workflow**:
1. **UserPreferenceAgent** - Analyze user's complete viewing history and rating patterns
2. **MovieDataAgent** - Identify genre gaps and unexplored categories
3. **RecommendationEngineAgent** - Generate analysis report and expansion recommendations
4. **ProxyAgent** - Format comprehensive analysis with actionable insights

### 4. Mood-Based Recommendations
```
I'm feeling stressed after a long work week and want to watch something uplifting and fun. Nothing too intense or heavy. What movies would help me relax and feel better?
```

**Expected Workflow**:
1. **UserPreferenceAgent** - Consider user's stress relief and mood preferences
2. **MovieDataAgent** - Find uplifting, light-hearted movies with positive themes
3. **RecommendationEngineAgent** - Recommend feel-good movies based on mood context
4. **ProxyAgent** - Present mood-appropriate suggestions with explanations

### 5. Director/Actor Discovery
```
I really enjoyed Christopher Nolan's movies. Can you recommend other directors with similar styles and some of their best films I should watch?
```

**Expected Workflow**:
1. **MovieDataAgent** - Analyze Christopher Nolan's filmography and directorial style
2. **UserPreferenceAgent** - Check user's history with similar directors
3. **RecommendationEngineAgent** - Recommend directors with similar styles and their top films
4. **ProxyAgent** - Present director recommendations with film suggestions

## Key Features

### Agent Collaboration
- Each agent operates within their specialized domain
- Clear handoffs between agents based on expertise
- Comprehensive utilization of all agents for complete responses

### Personalization
- Deep user preference analysis
- Viewing history consideration
- Contextual recommendations (mood, occasion, group viewing)

### Diverse Recommendations
- Popular mainstream options
- Hidden gems and indie films
- Genre exploration suggestions
- Trending content awareness

### Intelligent Explanations
- Clear reasoning for each recommendation
- Preference matching explanations
- Discovery and exploration rationale

## Integration with Existing System

The movie recommendation team integrates seamlessly with the existing MACAE architecture:

### Domain Detection
The orchestration system will recognize this as a MOVIE team based on agent composition:
- `MovieDataAgent` indicates movie domain specialization
- `UserPreferenceAgent` indicates recommendation system capability
- `RecommendationEngineAgent` confirms intelligent recommendation functionality

### Data Integration
- Uses existing RAG infrastructure for movie and user data
- Leverages existing reasoning capabilities for recommendation generation
- Maintains same security and privacy standards as retail team

### User Experience
- Same WebSocket-based real-time interaction
- Human-in-the-loop approval for recommendation plans
- Consistent API endpoints and response formatting

## Usage Instructions

1. **Upload the Team Configuration**: Place `movie_recommendation.json` in the `data/agent_teams/` directory
2. **Add Sample Data**: Upload the CSV files to `data/datasets/` directory  
3. **Select the Team**: Use the team selection API to switch to the Movie Recommendation team
4. **Test with Sample Prompts**: Try the provided sample prompts to see the collaborative agent workflow
5. **Customize**: Modify agent descriptions or add more specific movie datasets as needed

This movie recommendation system demonstrates the flexibility of the MACAE architecture for different domains while maintaining the same collaborative multi-agent principles used in the retail scenario.