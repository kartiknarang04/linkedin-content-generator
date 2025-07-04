# persona_evolution_enhanced.py
import streamlit as st
import json
import pandas as pd
from datetime import datetime, timedelta
import time
import os
from sentence_transformers import SentenceTransformer
import chromadb
from groq import Groq
import uuid
import numpy as np
import re

class PersonaEvolutionSystem:
    def __init__(self, chroma_path="chroma_db", groq_api_key=None):
        self.chroma_path = chroma_path
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        self.client = chromadb.PersistentClient(path=chroma_path)
        self.groq_client = Groq(api_key=self.groq_api_key) if self.groq_api_key else None
        
        # Your existing collection for reference posts
        try:
            self.posts_collection = self.client.get_collection(name="posts_collection")
        except:
            self.posts_collection = None
        
        # New collections for persona evolution
        self.user_stm_collection = self.client.get_or_create_collection(
            name="user_short_term_memory",
            metadata={"description": "User's recent posts and analysis"}
        )
        
        self.user_ltm_collection = self.client.get_or_create_collection(
            name="user_long_term_memory", 
            metadata={"description": "User's compressed personality patterns"}
        )
        
        self.persona_snapshots = self.client.get_or_create_collection(
            name="user_persona_snapshots",
            metadata={"description": "Current user persona states"}
        )
        # Memory Feeder Collections
        self.user_context_collection = self.client.get_or_create_collection(
            name="user_context_memory",
            metadata={"description": "User and company specific context information"}
        )

        self.company_info_collection = self.client.get_or_create_collection(
            name="company_info_memory", 
            metadata={"description": "Company details, culture, achievements, news"}
        )

        self.user_achievements_collection = self.client.get_or_create_collection(
            name="user_achievements_memory",
            metadata={"description": "User personal achievements, experiences, projects"}
        )

    def add_user_context(self, user_id: str, context_type: str, title: str, content: str, tags: list = None, importance: float = 0.5):
        """Add user-specific context information"""
        
        context_id = f"context_{user_id}_{int(datetime.now().timestamp())}"
        
        metadata = {
            "user_id": user_id,
            "context_type": context_type,  # personal, professional, achievement, experience
            "title": title,
            "tags": json.dumps(tags or []),
            "importance": float(importance),  # 0.0 to 1.0
            "timestamp": datetime.now().isoformat(),
            "usage_count": 0
        }
        
        self.user_context_collection.add(
            ids=[context_id],
            documents=[content],
            metadatas=[metadata]
        )
        
        return context_id

    def add_company_info(self, user_id: str, company_name: str, info_type: str, 
                        title: str, content: str, relevance: float = 0.5):
        """Add company-specific information"""
        
        company_id = f"company_{user_id}_{int(datetime.now().timestamp())}"
        
        metadata = {
            "user_id": user_id,
            "company_name": company_name,
            "info_type": info_type,  # culture, values, news, achievements, products, industry
            "title": title,
            "relevance": float(relevance),
            "timestamp": datetime.now().isoformat(),
            "usage_count": 0
        }
        
        self.company_info_collection.add(
            ids=[company_id],
            documents=[content],
            metadatas=[metadata]
        )
        
        return company_id

    def add_user_achievement(self, user_id: str, achievement_type: str, title: str, 
                            description: str, impact: str = "", date: str = "", 
                            skills_used: list = None):
        """Add user achievement or significant experience"""
        
        achievement_id = f"achievement_{user_id}_{int(datetime.now().timestamp())}"
        
        full_content = f"Achievement: {title}\nDescription: {description}"
        if impact:
            full_content += f"\nImpact: {impact}"
        if date:
            full_content += f"\nDate: {date}"
        if skills_used:
            full_content += f"\nSkills Used: {', '.join(skills_used)}"
        
        metadata = {
            "user_id": user_id,
            "achievement_type": achievement_type,  # project, award, milestone, learning
            "title": title,
            "impact": impact,
            "date": date,
            "skills_used": json.dumps(skills_used or []),
            "timestamp": datetime.now().isoformat(),
            "usage_count": 0
        }
        
        self.user_achievements_collection.add(
            ids=[achievement_id],
            documents=[full_content],
            metadatas=[metadata]
        )
        
        return achievement_id

    def get_relevant_context(self, user_id: str, query: str, max_results: int = 5):
        """Get relevant user/company context for content generation"""
        
        all_context = {
            "user_context": [],
            "company_info": [],
            "achievements": []
        }
        
        try:
            # Get relevant user context
            user_context = self.user_context_collection.query(
                query_texts=[query],
                where={"user_id": {"$eq": user_id}},
                n_results=max_results
            )
            
            if user_context['documents']:
                for i, (doc, meta) in enumerate(zip(user_context['documents'][0], user_context['metadatas'][0])):
                    all_context["user_context"].append({
                        "title": meta.get("title", ""),
                        "content": doc,
                        "context_type": meta.get("context_type", ""),
                        "importance": meta.get("importance", 0.5),
                        "tags": json.loads(meta.get("tags", "[]"))
                    })
            
            # Get relevant company info
            company_info = self.company_info_collection.query(
                query_texts=[query],
                where={"user_id": {"$eq": user_id}},
                n_results=max_results
            )
            
            if company_info['documents']:
                for i, (doc, meta) in enumerate(zip(company_info['documents'][0], company_info['metadatas'][0])):
                    all_context["company_info"].append({
                        "title": meta.get("title", ""),
                        "content": doc,
                        "company_name": meta.get("company_name", ""),
                        "info_type": meta.get("info_type", ""),
                        "relevance": meta.get("relevance", 0.5)
                    })
            
            # Get relevant achievements
            achievements = self.user_achievements_collection.query(
                query_texts=[query],
                where={"user_id": {"$eq": user_id}},
                n_results=max_results
            )
            
            if achievements['documents']:
                for i, (doc, meta) in enumerate(zip(achievements['documents'][0], achievements['metadatas'][0])):
                    all_context["achievements"].append({
                        "title": meta.get("title", ""),
                        "content": doc,
                        "achievement_type": meta.get("achievement_type", ""),
                        "impact": meta.get("impact", ""),
                        "skills_used": json.loads(meta.get("skills_used", "[]"))
                    })
        
        except Exception as e:
            st.error(f"Error retrieving context: {e}")
        
        return all_context

    def update_context_usage(self, collection, context_id: str):
        """Update usage count for context items"""
        try:
            data = collection.get(ids=[context_id])
            if data['ids']:
                metadata = data['metadatas'][0]
                metadata['usage_count'] = int(metadata.get('usage_count', 0)) + 1
                
                collection.delete(ids=[context_id])
                collection.add(
                    ids=[context_id],
                    documents=data['documents'],
                    metadatas=[metadata]
                )
        except:
            pass
    def calculate_engagement_score(self, likes=0, comments=0, shares=0, views=0):
        """Calculate normalized engagement score"""
        # Weighted engagement formula
        engagement_raw = (likes * 1.0) + (comments * 3.0) + (shares * 5.0) + (views * 0.1)
        
        # Normalize to 0-1 scale (adjust max_expected based on your typical engagement)
        max_expected = 1000  # Adjust this based on typical high-performing posts
        engagement_normalized = min(engagement_raw / max_expected, 1.0)
        
        return max(engagement_normalized, 0.1)  # Minimum score of 0.1
    
    def add_user_post_to_memory(self, user_id: str, post_content: str, topic: str, post_type: str = "Generated", engagement_data: dict = None):
        """Add user's post (generated or actual) to their memory system with engagement tracking"""
        
        if not self.groq_client:
            st.error("Groq API key not found")
            return
        
        # Calculate engagement score if data provided
        engagement_score = 0.5  # Default for generated posts
        if engagement_data:
            engagement_score = self.calculate_engagement_score(
                likes=engagement_data.get('likes', 0),
                comments=engagement_data.get('comments', 0),
                shares=engagement_data.get('shares', 0),
                views=engagement_data.get('views', 0)
            )
        
        # Enhanced analysis prompt that considers engagement
        analysis_prompt = f"""
        Analyze this LinkedIn post and return a JSON object. Consider that this post had an engagement level of {engagement_score:.2f}/1.0:
        
        Post: "{post_content}"
        
        Focus on identifying what made this post {('highly engaging' if engagement_score > 0.7 else 'moderately engaging' if engagement_score > 0.4 else 'less engaging')}.
        
        Return ONLY a valid JSON object with this exact structure:
        {{
            "topic": "main topic/theme",
            "tone": "dominant tone",
            "belief": "key belief or stance expressed",
            "style_elements": ["element1", "element2"],
            "post_type": "type",
            "hooks": ["hook1", "hook2"],
            "structure": "how the post is structured",
            "cta_type": "call to action type if any",
            "voice_characteristics": ["characteristic1", "characteristic2"],
            "engagement_factors": ["factor1", "factor2"],
            "success_elements": ["element1", "element2"]
        }}
        """
        
        try:
            response = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": analysis_prompt}],
                model="llama3-8b-8192",
                temperature=0.3
            )            

            # Clean and parse JSON response
            response_content = response.choices[0].message.content.strip()
            
            # Check if response is empty
            if not response_content:
                st.error("Empty response from AI")
                response_content = "{}"
            
            # Remove any markdown code blocks if present
            response_content = re.sub(r'```json\s*|\s*```', '', response_content)

            # Extract JSON from response text
            json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = response_content

            try:
                analysis = json.loads(json_str)
            except json.JSONDecodeError as e:
                st.error(f"JSON parsing error: {e}")
                st.error(f"Raw response: {response_content}")
                # Fallback with default values
                analysis = {
                    "topic": topic,
                    "tone": "Professional",
                    "belief": "Growth mindset",
                    "style_elements": ["Clear", "Engaging"],
                    "post_type": post_type,
                    "hooks": ["Question"],
                    "structure": "Hook-Content-Action",
                    "cta_type": "Engagement",
                    "voice_characteristics": ["Professional", "Authentic"],
                    "engagement_factors": ["Relatable", "Actionable"],
                    "success_elements": ["Clear message", "Call to action"]
                }
            
            # Create STM entry with engagement data
            entry_id = f"stm_{user_id}_{int(datetime.now().timestamp())}"
            
            # Convert lists to JSON strings for ChromaDB compatibility
            metadata = {
                "user_id": user_id,
                "topic": str(analysis.get("topic", topic)),
                "tone": str(analysis.get("tone", "Professional")),
                "belief": str(analysis.get("belief", "")),
                "style_elements": json.dumps(analysis.get("style_elements", [])),
                "post_type": str(analysis.get("post_type", post_type)),
                "hooks": json.dumps(analysis.get("hooks", [])),
                "structure": str(analysis.get("structure", "")),
                "cta_type": str(analysis.get("cta_type", "")),
                "voice_characteristics": json.dumps(analysis.get("voice_characteristics", [])),
                "engagement_factors": json.dumps(analysis.get("engagement_factors", [])),
                "success_elements": json.dumps(analysis.get("success_elements", [])),
                "engagement_score": float(engagement_score),
                "likes": int(engagement_data.get('likes', 0) if engagement_data else 0),
                "comments": int(engagement_data.get('comments', 0) if engagement_data else 0),
                "shares": int(engagement_data.get('shares', 0) if engagement_data else 0),
                "views": int(engagement_data.get('views', 0) if engagement_data else 0),
                "timestamp": datetime.now().isoformat(),
                "processed": "false"
            }
            
            self.user_stm_collection.add(
                ids=[entry_id],
                documents=[post_content],
                metadatas=[metadata]
            )
            
            # Check if we need to compress to LTM (every 5 posts)
            stm_count = len(self.user_stm_collection.get(
                where={"$and": [{"user_id": {"$eq": user_id}}, {"processed": {"$eq": "false"}}]}
            )['ids'])
            
            if stm_count >= 5:
                self.compress_user_stm_to_ltm(user_id)
                
        except Exception as e:
            st.error(f"Error analyzing post: {e}")
            import traceback
            st.error(f"Full traceback: {traceback.format_exc()}")

    def compress_user_stm_to_ltm(self, user_id: str):
        """Compress user's STM to LTM with engagement-aware weighting"""
        
        # Get unprocessed STM entries
        stm_data = self.user_stm_collection.get(
            where={"$and": [{"user_id": {"$eq": user_id}}, {"processed": {"$eq": "false"}}]}
        )
        
        if len(stm_data['ids']) < 5:
            return
        
        # Sort by engagement score to prioritize high-performing content
        posts_with_engagement = []
        for i, meta in enumerate(stm_data['metadatas']):
            posts_with_engagement.append({
                'document': stm_data['documents'][i],
                'metadata': meta,
                'engagement_score': float(meta.get('engagement_score', 0.5))
            })
        
        # Sort by engagement (highest first)
        posts_with_engagement.sort(key=lambda x: x['engagement_score'], reverse=True)
        
        # Create weighted analysis
        high_engagement_posts = [p for p in posts_with_engagement if p['engagement_score'] > 0.6]
        medium_engagement_posts = [p for p in posts_with_engagement if 0.3 <= p['engagement_score'] <= 0.6]
        low_engagement_posts = [p for p in posts_with_engagement if p['engagement_score'] < 0.3]
        
        # Build engagement-weighted context
        context_summary = f"""
        ENGAGEMENT-WEIGHTED POST ANALYSIS ({len(stm_data['ids'])} posts):
        
        HIGH ENGAGEMENT POSTS ({len(high_engagement_posts)} posts):
        {chr(10).join([f"- {p['document'][:150]}... (Score: {p['engagement_score']:.2f})" for p in high_engagement_posts])}
        
        MEDIUM ENGAGEMENT POSTS ({len(medium_engagement_posts)} posts):
        {chr(10).join([f"- {p['document'][:100]}... (Score: {p['engagement_score']:.2f})" for p in medium_engagement_posts])}
        
        LOW ENGAGEMENT POSTS ({len(low_engagement_posts)} posts):
        {chr(10).join([f"- {p['document'][:80]}... (Score: {p['engagement_score']:.2f})" for p in low_engagement_posts])}
        """
        
        # Enhanced compression prompt with engagement awareness
        compression_prompt = f"""
        Analyze these {len(stm_data['ids'])} posts to understand the user's evolving voice, PRIORITIZING patterns from high-engagement posts:
        
        {context_summary}
        
        Create a personality evolution summary as a JSON object:
        
        Return ONLY a valid JSON object with this exact structure:
        {{
            "period_summary": "brief description focusing on what worked best",
            "dominant_tones": ["tone1", "tone2"],
            "core_beliefs": ["belief1", "belief2"],
            "writing_patterns": ["pattern1", "pattern2"],
            "voice_evolution": "how the voice changed",
            "style_preferences": ["preference1", "preference2"],
            "content_themes": ["theme1", "theme2"],
            "engagement_style": "how they engage with audience",
            "personality_traits": ["trait1", "trait2"],
            "success_formulas": ["formula1", "formula2"],
            "high_engagement_hooks": ["hook1", "hook2"],
            "winning_structures": ["structure1", "structure2"],
            "engagement_strengths": ["strength1", "strength2"],
            "voice_confidence": 0.7,
            "uniqueness_score": 0.8,
            "engagement_optimization": 0.9
        }}
        
        CRITICAL: Prioritize patterns from posts with engagement scores > 0.6.
        """
        
        try:
            response = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": compression_prompt}],
                model="llama3-8b-8192",
                temperature=0.3
            )
            
            # Clean and parse JSON response
            response_content = response.choices[0].message.content.strip()
            
            # Check if response is empty
            if not response_content:
                st.error("Empty response from AI for LTM compression")
                response_content = "{}"
            
            response_content = re.sub(r'```json\s*|\s*```', '', response_content)
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = response_content
            
            try:
                ltm_analysis = json.loads(json_str)
            except json.JSONDecodeError as e:
                st.error(f"JSON parsing error in LTM: {e}")
                st.error(f"Raw response: {response_content}")
                # Use fallback default analysis
                ltm_analysis = {
                    "period_summary": "Analysis period summary",
                    "dominant_tones": ["Professional"],
                    "core_beliefs": ["Growth mindset"],
                    "writing_patterns": ["Clear communication"],
                    "voice_evolution": "Voice developing",
                    "style_preferences": ["Professional"],
                    "content_themes": ["Professional development"],
                    "engagement_style": "Professional engagement",
                    "personality_traits": ["Professional"],
                    "success_formulas": ["Hook-Content-Action"],
                    "high_engagement_hooks": ["Question"],
                    "winning_structures": ["Problem-Solution"],
                    "engagement_strengths": ["Clear", "Professional"],
                    "voice_confidence": 0.7,
                    "uniqueness_score": 0.8,
                    "engagement_optimization": 0.9
                }
            
            # Calculate weighted metrics
            avg_engagement = np.mean([p['engagement_score'] for p in posts_with_engagement])
            max_engagement = max([p['engagement_score'] for p in posts_with_engagement])
            engagement_trend = "improving" if len(high_engagement_posts) > len(low_engagement_posts) else "mixed"
            
            # Create enhanced LTM document
            ltm_id = f"ltm_{user_id}_{int(datetime.now().timestamp())}"
            
            ltm_document = f"""
            User Writing Period Analysis (Engagement-Weighted)
            Period: {datetime.now().strftime('%Y-%m-%d')}
            Posts Analyzed: {len(stm_data['ids'])}
            Average Engagement: {avg_engagement:.2f}
            Peak Engagement: {max_engagement:.2f}
            Engagement Trend: {engagement_trend}
            
            Summary: {ltm_analysis.get('period_summary', '')}
            Dominant Tones: {', '.join(ltm_analysis.get('dominant_tones', []))}
            Core Beliefs: {', '.join(ltm_analysis.get('core_beliefs', []))}
            Writing Patterns: {', '.join(ltm_analysis.get('writing_patterns', []))}
            Voice Evolution: {ltm_analysis.get('voice_evolution', '')}
            Style Preferences: {', '.join(ltm_analysis.get('style_preferences', []))}
            Content Themes: {', '.join(ltm_analysis.get('content_themes', []))}
            Engagement Style: {ltm_analysis.get('engagement_style', '')}
            Personality Traits: {', '.join(ltm_analysis.get('personality_traits', []))}
            Success Formulas: {', '.join(ltm_analysis.get('success_formulas', []))}
            High-Engagement Hooks: {', '.join(ltm_analysis.get('high_engagement_hooks', []))}
            Winning Structures: {', '.join(ltm_analysis.get('winning_structures', []))}
            Engagement Strengths: {', '.join(ltm_analysis.get('engagement_strengths', []))}
            """
            
            # Store in LTM with enhanced metadata (convert all lists to strings)
            ltm_metadata = {
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "post_count": len(stm_data['ids']),
                "avg_engagement": float(avg_engagement),
                "max_engagement": float(max_engagement),
                "high_engagement_count": len(high_engagement_posts),
                "engagement_trend": str(engagement_trend),
                "period_summary": str(ltm_analysis.get('period_summary', '')),
                "dominant_tones": json.dumps(ltm_analysis.get('dominant_tones', [])),
                "core_beliefs": json.dumps(ltm_analysis.get('core_beliefs', [])),
                "writing_patterns": json.dumps(ltm_analysis.get('writing_patterns', [])),
                "voice_evolution": str(ltm_analysis.get('voice_evolution', '')),
                "style_preferences": json.dumps(ltm_analysis.get('style_preferences', [])),
                "content_themes": json.dumps(ltm_analysis.get('content_themes', [])),
                "engagement_style": str(ltm_analysis.get('engagement_style', '')),
                "personality_traits": json.dumps(ltm_analysis.get('personality_traits', [])),
                "success_formulas": json.dumps(ltm_analysis.get('success_formulas', [])),
                "high_engagement_hooks": json.dumps(ltm_analysis.get('high_engagement_hooks', [])),
                "winning_structures": json.dumps(ltm_analysis.get('winning_structures', [])),
                "engagement_strengths": json.dumps(ltm_analysis.get('engagement_strengths', [])),
                "voice_confidence": float(ltm_analysis.get('voice_confidence', 0.7)),
                "uniqueness_score": float(ltm_analysis.get('uniqueness_score', 0.8)),
                "engagement_optimization": float(ltm_analysis.get('engagement_optimization', 0.9))
            }
            
            self.user_ltm_collection.add(
                ids=[ltm_id],
                documents=[ltm_document],
                metadatas=[ltm_metadata]
            )
            
            # Mark STM as processed
            for entry_id in stm_data['ids']:
                old_data = self.user_stm_collection.get(ids=[entry_id])
                metadata = old_data['metadatas'][0]
                metadata['processed'] = "true"
                
                self.user_stm_collection.delete(ids=[entry_id])
                self.user_stm_collection.add(
                    ids=[entry_id],
                    documents=old_data['documents'],
                    metadatas=[metadata]
                )
            
            # Update persona snapshot with engagement insights
            self.update_user_persona_snapshot(user_id)
            
            st.success(f"✅ Compressed {len(stm_data['ids'])} posts to long-term memory!")
            
        except Exception as e:
            st.error(f"Error compressing to LTM: {e}")
            import traceback
            st.error(f"Full traceback: {traceback.format_exc()}")
    def update_user_persona_snapshot(self, user_id: str):
        """Update user's current persona snapshot with engagement-aware insights"""
        
        # Get recent LTM entries
        recent_ltm = self.user_ltm_collection.get(
            where={"user_id": {"$eq": user_id}}
        )
        
        if not recent_ltm['ids']:
            return
        
        # Get the most recent LTM entries (last 3) prioritizing high-engagement periods
        sorted_ltm = list(zip(recent_ltm['documents'], recent_ltm['metadatas']))
        sorted_ltm.sort(key=lambda x: (x[1].get('avg_engagement', 0), x[1]['timestamp']), reverse=True)
        recent_context = "\n\n".join([doc for doc, meta in sorted_ltm[:3]])
        
        # Calculate overall engagement metrics safely
        engagement_metrics = {
            'avg_engagement': np.mean([meta.get('avg_engagement', 0.5) for doc, meta in sorted_ltm]),
            'peak_engagement': max([meta.get('max_engagement', 0.5) for doc, meta in sorted_ltm]),
            'high_engagement_ratio': np.mean([meta.get('high_engagement_count', 0) / max(meta.get('post_count', 1), 1) for doc, meta in sorted_ltm])
        }
        
        snapshot_prompt = f"""
        Based on this user's writing evolution, create their current persona snapshot:
        
        ENGAGEMENT PERFORMANCE:
        - Average Engagement: {engagement_metrics['avg_engagement']:.2f}/1.0
        - Peak Engagement: {engagement_metrics['peak_engagement']:.2f}/1.0
        - High-Engagement Ratio: {engagement_metrics['high_engagement_ratio']:.2f}
        
        EVOLUTION CONTEXT:
        {recent_context}
        
        Return ONLY a valid JSON object with this exact structure:
        {{
            "current_voice": "dominant voice description",
            "primary_tones": ["tone1", "tone2"],
            "core_beliefs": ["belief1", "belief2"],
            "writing_signature": "unique writing characteristics",
            "preferred_structures": ["structure1", "structure2"],
            "content_focus_areas": ["area1", "area2"],
            "engagement_approach": "how they connect with audience",
            "success_patterns": ["pattern1", "pattern2"],
            "winning_hooks": ["hook1", "hook2"],
            "engagement_strengths": ["strength1", "strength2"],
            "voice_maturity_level": 0.8,
            "engagement_mastery": 0.7,
            "personality_blend": "combination of traits",
            "evolution_direction": "how voice is trending"
        }}
        
        CRITICAL: Weight all insights based on engagement success.
        """
        
        try:
            response = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": snapshot_prompt}],
                model="llama3-8b-8192",
                temperature=0.3
            )
            
            # Clean and parse JSON response
            response_content = response.choices[0].message.content.strip()
            
            # Check if response is empty
            if not response_content:
                st.error("Empty response from AI for persona snapshot")
                response_content = "{}"
            
            response_content = re.sub(r'```json\s*|\s*```', '', response_content)
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = response_content
            
            try:
                snapshot = json.loads(json_str)
            except json.JSONDecodeError as e:
                st.error(f"JSON parsing error in snapshot: {e}")
                st.error(f"Raw response: {response_content}")
                # Use fallback snapshot
                snapshot = {
                    "current_voice": "Professional and engaging",
                    "primary_tones": ["Professional", "Friendly"],
                    "core_beliefs": ["Growth mindset", "Continuous learning"],
                    "writing_signature": "Clear and actionable content",
                    "preferred_structures": ["Hook-Insight-Action"],
                    "content_focus_areas": ["Professional development"],
                    "engagement_approach": "Ask questions and provide value",
                    "success_patterns": ["Start with story", "End with action"],
                    "winning_hooks": ["Question", "Story"],
                    "engagement_strengths": ["Authentic", "Actionable"],
                    "voice_maturity_level": 0.8,
                    "engagement_mastery": 0.7,
                    "personality_blend": "Professional yet approachable",
                    "evolution_direction": "Toward more engaging content"
                }
            
            # Store enhanced persona snapshot
            snapshot_id = f"persona_{user_id}"
            
            snapshot_document = f"""
            Current Persona Snapshot for User: {user_id} (Engagement-Optimized)
            Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            
            ENGAGEMENT PERFORMANCE:
            Average Engagement: {engagement_metrics['avg_engagement']:.2f}/1.0
            Peak Engagement: {engagement_metrics['peak_engagement']:.2f}/1.0
            High-Performance Ratio: {engagement_metrics['high_engagement_ratio']:.1%}
            
            EVOLVED VOICE PROFILE:
            Voice Description: {snapshot.get('current_voice', '')}
            Primary Tones: {', '.join(snapshot.get('primary_tones', []))}
            Core Beliefs: {', '.join(snapshot.get('core_beliefs', []))}
            Writing Signature: {snapshot.get('writing_signature', '')}
            Preferred Structures: {', '.join(snapshot.get('preferred_structures', []))}
            Content Focus: {', '.join(snapshot.get('content_focus_areas', []))}
            Engagement Style: {snapshot.get('engagement_approach', '')}
            
            SUCCESS FORMULAS:
            Success Patterns: {', '.join(snapshot.get('success_patterns', []))}
            Winning Hooks: {', '.join(snapshot.get('winning_hooks', []))}
            Engagement Strengths: {', '.join(snapshot.get('engagement_strengths', []))}
            
            MATURITY METRICS:
            Voice Maturity: {snapshot.get('voice_maturity_level', 0.5)}
            Engagement Mastery: {snapshot.get('engagement_mastery', 0.5)}
            Personality Blend: {snapshot.get('personality_blend', '')}
            Evolution Direction: {snapshot.get('evolution_direction', '')}
            """
            
            # Convert all lists to JSON strings for ChromaDB metadata
            snapshot_metadata = {
                "user_id": user_id,
                "last_updated": datetime.now().isoformat(),
                "avg_engagement": float(engagement_metrics['avg_engagement']),
                "peak_engagement": float(engagement_metrics['peak_engagement']),
                "high_engagement_ratio": float(engagement_metrics['high_engagement_ratio']),
                "current_voice": str(snapshot.get('current_voice', '')),
                "primary_tones": json.dumps(snapshot.get('primary_tones', [])),
                "core_beliefs": json.dumps(snapshot.get('core_beliefs', [])),
                "writing_signature": str(snapshot.get('writing_signature', '')),
                "preferred_structures": json.dumps(snapshot.get('preferred_structures', [])),
                "content_focus_areas": json.dumps(snapshot.get('content_focus_areas', [])),
                "engagement_approach": str(snapshot.get('engagement_approach', '')),
                "success_patterns": json.dumps(snapshot.get('success_patterns', [])),
                "winning_hooks": json.dumps(snapshot.get('winning_hooks', [])),
                "engagement_strengths": json.dumps(snapshot.get('engagement_strengths', [])),
                "voice_maturity_level": float(snapshot.get('voice_maturity_level', 0.5)),
                "engagement_mastery": float(snapshot.get('engagement_mastery', 0.5)),
                "personality_blend": str(snapshot.get('personality_blend', '')),
                "evolution_direction": str(snapshot.get('evolution_direction', ''))
            }
            
            # Delete existing and add new
            try:
                self.persona_snapshots.delete(ids=[snapshot_id])
            except:
                pass
            
            self.persona_snapshots.add(
                ids=[snapshot_id],
                documents=[snapshot_document],
                metadatas=[snapshot_metadata]
            )
            
            st.success("✅ Persona snapshot updated successfully!")
            
        except Exception as e:
            st.error(f"Error updating persona snapshot: {e}")
            import traceback
            st.error(f"Full traceback: {traceback.format_exc()}")
    
    def get_engagement_insights(self, user_id: str):
        """Get user's engagement performance insights"""
        try:
            # Get recent posts
            stm_data = self.user_stm_collection.get( where={"user_id": {"$eq": user_id}})  
            if not stm_data['ids']:
                return None
            
            engagement_scores = [float(meta.get('engagement_score', 0.5)) for meta in stm_data['metadatas']]
            
            return {
                'total_posts': len(engagement_scores),
                'avg_engagement': np.mean(engagement_scores),
                'peak_engagement': max(engagement_scores),
                'high_performers': len([s for s in engagement_scores if s > 0.6]),
                'engagement_trend': 'improving' if len(engagement_scores) > 3 and np.mean(engagement_scores[-3:]) > np.mean(engagement_scores[:-3]) else 'stable'
            }
        except:
            return None
def enhanced_generate_content_with_groq_v2(query, similar_posts, user_persona, creator_preferences, persona_system, user_id):
    """Enhanced content generation with memory feeder context"""
    
    try:
        groq_api_key = persona_system.groq_api_key
        if not groq_api_key:
            st.error("GROQ_API_KEY not found")
            return None, None, None
        
        client = Groq(api_key=groq_api_key)
        
        # Get evolved persona (existing code)
        evolved_persona = None
        try:
            persona_data = persona_system.persona_snapshots.get(
                ids=[f"persona_{user_id}"]
            )
            if persona_data['ids']:
                evolved_persona = persona_data['metadatas'][0]
        except:
            pass
        
        # Get engagement insights (existing code)
        engagement_insights = persona_system.get_engagement_insights(user_id)
        
        # NEW: Get relevant memory feeder context
        relevant_context = persona_system.get_relevant_context(user_id, query)
        
        # Build memory context for prompt
        memory_context = ""
        
        # Add user context
        if relevant_context["user_context"]:
            memory_context += "\n\nYOUR PERSONAL CONTEXT:\n"
            for ctx in relevant_context["user_context"]:
                memory_context += f"- {ctx['title']}: {ctx['content']}\n"
                memory_context += f"  Type: {ctx['context_type']}, Importance: {ctx['importance']}\n"
        
        # Add company context
        if relevant_context["company_info"]:
            memory_context += "\n\nYOUR COMPANY CONTEXT:\n"
            for company in relevant_context["company_info"]:
                memory_context += f"- {company['title']}: {company['content']}\n"
                memory_context += f"  Company: {company['company_name']}, Type: {company['info_type']}\n"
        
        # Add achievements context
        if relevant_context["achievements"]:
            memory_context += "\n\nYOUR ACHIEVEMENTS & EXPERIENCES:\n"
            for achievement in relevant_context["achievements"]:
                memory_context += f"- {achievement['title']}: {achievement['content']}\n"
                if achievement['impact']:
                    memory_context += f"  Impact: {achievement['impact']}\n"
        
        # Enhanced user context with engagement data (existing code)
        user_context = ""
        if evolved_persona:
            user_context = f"""

YOUR ENGAGEMENT-OPTIMIZED VOICE (based on your most successful posts):
- Current Voice: {evolved_persona.get('current_voice', 'Professional')}
- Primary Tones: {', '.join(evolved_persona.get('primary_tones', ['Professional']))}
- Core Beliefs (from high-engagement posts): {', '.join(evolved_persona.get('core_beliefs', ['Growth mindset']))}
- Writing Signature: {evolved_persona.get('writing_signature', 'Clear and engaging')}
- Success Patterns: {', '.join(evolved_persona.get('success_patterns', ['Hook-Insight-Action']))}
- Winning Hooks: {', '.join(evolved_persona.get('winning_hooks', ['Question', 'Story']))}
- Engagement Strengths: {', '.join(evolved_persona.get('engagement_strengths', ['Authentic', 'Actionable']))}
- Voice Maturity: {evolved_persona.get('voice_maturity_level', 0.5)}/1.0
- Engagement Mastery: {evolved_persona.get('engagement_mastery', 0.5)}/1.0
        """
        
        # Add engagement performance context (existing code)
        if engagement_insights:
            user_context += f"""

YOUR ENGAGEMENT PERFORMANCE:
- Total Posts: {engagement_insights['total_posts']}
- Average Engagement: {engagement_insights['avg_engagement']:.2f}/1.0
- Peak Performance: {engagement_insights['peak_engagement']:.2f}/1.0
- High Performers: {engagement_insights['high_performers']} posts
- Trend: {engagement_insights['engagement_trend']}
        """
        
        # Get similar posts from user's own history (existing code)
        user_similar_posts = ""
        try:
            user_posts = persona_system.user_stm_collection.query(
                query_texts=[query],
                where={"user_id": {"$eq": user_id}},
                n_results=5
            )
            if user_posts['documents']:
                posts_with_meta = list(zip(user_posts['documents'], user_posts['metadatas']))
                posts_with_meta.sort(key=lambda x: float(x[1].get('engagement_score', 0)), reverse=True)
                
                user_similar_posts = f"""

YOUR HIGH-PERFORMING POSTS ON SIMILAR TOPICS:
{chr(10).join([f"- {doc[:200]}... (Engagement: {meta.get('engagement_score', 0):.2f})" for doc, meta in posts_with_meta[:3]])}
        """
        except:
            pass
        
        # Original context preparation (existing code)
        posts_context = ""
        if similar_posts:
            for i, post in enumerate(similar_posts, 1):
                posts_context += f"\n--- Reference Post {i} (by {post.get('profile_name', 'Unknown')}) ---\n"
                posts_context += f"Similarity Score: {post.get('similarity_score', 0.0):.3f}\n"
                posts_context += f"Content: {post.get('post_text', '')}\n"
        else:
            posts_context = "\n--- No reference posts available ---\n"
        
        user_profile_context = f"""
User Profile:
- Name: {user_persona['basic_info']['name']}
- Role: {user_persona['basic_info']['role']}
- LinkedIn Goal: {user_persona['basic_info']['linkedin_goal']}
- Preferred Content Types: {', '.join(user_persona['content_preferences']['preferred_content_types'])}
- Preferred Tone: {', '.join(user_persona['content_preferences']['preferred_tone'])}
"""
        
        creator_context = ""
        if 'reference_info' in user_persona:
            creator_context += f"\nWhat you like about reference creators: {user_persona['reference_info']['creator_likes']}\n"
            
            for creator in user_persona['reference_info']['reference_creators']:
                if 'preferences' in creator:
                    creator_context += f"\nAbout {creator['name']}:\n"
                    prefs = creator['preferences']
                    if prefs.get('tone'):
                        creator_context += f"- Liked tone: {', '.join(prefs['tone'])}\n"
                    if prefs.get('content_type'):
                        creator_context += f"- Liked content types: {', '.join(prefs['content_type'])}\n"
                    if prefs.get('style'):
                        creator_context += f"- Liked style: {', '.join(prefs['style'])}\n"
        
        # ENHANCED PROMPT with memory feeder context
        prompt = f"""
You are creating LinkedIn content for a user whose writing voice has evolved based on ENGAGEMENT SUCCESS PATTERNS.

USER QUERY: "{query}"

{user_profile_context}

{user_context}

{memory_context}

{user_similar_posts}

{creator_context}

REFERENCE POSTS (for inspiration):
{posts_context}

CRITICAL INSTRUCTIONS FOR ENGAGEMENT-OPTIMIZED CONTENT WITH PERSONAL CONTEXT:
1. Write in the user's EVOLVED VOICE prioritizing their highest-performing patterns
2. Use their winning hooks and success formulas from high-engagement posts
3. INCORPORATE relevant personal/company context naturally into the content
4. Reference their achievements, experiences, or company details when relevant
5. Make the content authentic by weaving their specific context into the narrative
6. Address the query: "{query}" using their most successful voice elements AND personal context
7. Apply their engagement strengths and proven structures
8. Include 3-5 relevant hashtags based on their successful content themes and context
9. Keep within 1300 characters for optimal LinkedIn engagement
10. Make it authentically theirs while maximizing engagement potential using their real experiences

Generate a LinkedIn post that combines their authentic evolved voice with their highest-engagement elements AND relevant personal/company context:
"""
        
        # Generate content
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-8b-8192",
            temperature=0.7,
            max_tokens=1000
        )
        
        generated_content = chat_completion.choices[0].message.content
        
        # Update usage counts for used context
        for ctx in relevant_context["user_context"]:
            # You'd need to track which context was actually used
            pass
        
        # Add this generated post to their memory for continued evolution
        persona_system.add_user_post_to_memory(user_id, generated_content, query, "Generated")
        
        return generated_content, evolved_persona, engagement_insights
        
    except Exception as e:
        st.error(f"Error generating content: {str(e)}")
        return None, None, None

# Additional helper function for engagement tracking UI
def display_engagement_dashboard(persona_system, user_id):
    """Display user's engagement performance dashboard"""
    
    insights = persona_system.get_engagement_insights(user_id)
    
    if not insights:
        st.info("Generate a few posts to see your engagement insights!")
        return
    
    st.markdown("### 📊 Your Engagement Performance")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Posts", insights['total_posts'])
    
    with col2:
        st.metric("Avg Engagement", f"{insights['avg_engagement']:.2f}")
    
    with col3:
        st.metric("Peak Score", f"{insights['peak_engagement']:.2f}")
    
    with col4:
        st.metric("High Performers", f"{insights['high_performers']}")
    
    # Engagement trend indicator
    trend_color = "🟢" if insights['engagement_trend'] == 'improving' else "🟡"
    st.markdown(f"**Trend:** {trend_color} {insights['engagement_trend'].title()}")
def display_enhanced_content_generation_page():
    """Enhanced content generation page with engagement-aware persona evolution"""
    
    # Initialize persona system
    if 'persona_system' not in st.session_state or not hasattr(st.session_state.persona_system, 'user_context_collection'):
        st.session_state.persona_system = PersonaEvolutionSystem()
        
    persona_system = st.session_state.persona_system
    
    # ===== ADD THIS QUICK TEST DATA HERE =====
    # Quick test setup - bypass profile requirements for testing
    if not st.session_state.get('form_completed', False):
        st.session_state.form_completed = True
        st.session_state.persona_dict = {
            'basic_info': {
                'name': 'Test User',
                'role': 'Software Developer',
                'linkedin_goal': 'Build professional network and share insights'
            },
            'content_preferences': {
                'preferred_content_types': ['Tips', 'Stories', 'Insights'],
                'preferred_tone': ['Professional', 'Friendly', 'Inspiring']
            },
            'reference_info': {
                'creator_likes': 'Authentic storytelling and practical advice',
                'reference_creators': [
                    {
                        'name': 'Test Creator',
                        'preferences': {
                            'tone': ['Professional', 'Authentic'],
                            'content_type': ['Stories', 'Tips'],
                            'style': ['Conversational', 'Actionable']
                        }
                    }
                ]
            }
        }
        # Also initialize creator preferences
        st.session_state.creator_preferences = {}
    # ===== END OF QUICK TEST DATA =====
    
    # Check profile setup (this will now pass with our test data)
    if not st.session_state.get('form_completed', False) or not st.session_state.get('persona_dict'):
        st.warning("⚠️ Please complete your profile setup first!")
        if st.button("Go to Profile Setup"):
            st.session_state.current_page = "profile_setup"
            st.rerun()
        return
    
    # Initialize persona system
    if 'persona_system' not in st.session_state:
        st.session_state.persona_system = PersonaEvolutionSystem()
    
    persona_system = st.session_state.persona_system
    
    st.markdown("""
    <div class="content-card">
        <h2 style="color: #1a365d; font-size: 32px;">🚀 AI Content Generation with Engagement-Optimized Persona Evolution</h2>
        <p style="color: #2d3748; font-size: 20px; font-weight: 600;">Generate content that evolves based on your most engaging posts.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check profile setup
    if not st.session_state.get('form_completed', False) or not st.session_state.get('persona_dict'):
        st.warning("⚠️ Please complete your profile setup first!")
        if st.button("Go to Profile Setup"):
            st.session_state.current_page = "profile_setup"
            st.rerun()
        return
    
    # Get user ID
    user_id = st.session_state.persona_dict['basic_info']['name'].replace(" ", "_").lower()
    
    # Display engagement dashboard
    display_engagement_dashboard(persona_system, user_id)
    
    st.markdown("---")
    
    # Content generation section
    st.markdown("### 📝 Generate Your Next LinkedIn Post")
    
    # Two-column layout for input and engagement tracking
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Query input
        query = st.text_area(
            "What would you like to write about?",
            placeholder="E.g., 'leadership lessons from my recent project failure' or 'AI tools that changed my workflow'",
            height=100
        )
    
    with col2:
        st.markdown("#### 📊 Add Engagement Data")
        st.markdown("*(Optional: Track real post performance)*")
        
        with st.expander("Track Post Performance"):
            likes = st.number_input("Likes", min_value=0, value=0)
            comments = st.number_input("Comments", min_value=0, value=0)
            shares = st.number_input("Shares", min_value=0, value=0)
            views = st.number_input("Views", min_value=0, value=0)
            
            engagement_data = {
                'likes': likes,
                'comments': comments,
                'shares': shares,
                'views': views
            } if any([likes, comments, shares, views]) else None
    
    # Generate button
    if st.button("🚀 Generate Content", type="primary", use_container_width=True):
        if not query.strip():
            st.warning("Please enter what you'd like to write about!")
            return
        
        if not persona_system.posts_collection:
            st.error("No reference posts collection found. Please ensure the database is properly set up.")
            return
        
        # Initialize formatted_posts with default value to avoid UnboundLocalError
        formatted_posts = []

        with st.spinner("🧠 Analyzing your evolved voice and generating content..."):
            try:
                # Get similar posts from reference collection
                similar_posts = persona_system.posts_collection.query(
                    query_texts=[query],
                    n_results=5
                )

                # Format similar posts
                for i, (doc, metadata) in enumerate(zip(similar_posts['documents'][0], similar_posts['metadatas'][0])):
                    formatted_posts.append({
                        'post_text': doc,
                        'profile_name': metadata.get('profile_name', 'Unknown'),
                        'similarity_score': similar_posts['distances'][0][i] if similar_posts['distances'] else 0.0
                    })

            except Exception as e:
                st.error(f"Error fetching similar posts: {str(e)}")
                # formatted_posts remains empty list, which is safe to use

            # Generate content using the formatted_posts (empty list if error occurred)
            try:
                result = enhanced_generate_content_with_groq_v2(
                    query,
                    formatted_posts,
                    st.session_state.persona_dict,
                    st.session_state.get('creator_preferences', {}),
                    persona_system,
                    user_id
                )
                
                if result[0]:  # If content was generated
                    generated_content, evolved_persona, engagement_insights = result
                    
                    # Display generated content
                    st.markdown(f"""
                <div class="generated-content">
                    <div style="font-size: 16px; line-height: 1.6; white-space: pre-wrap; color: #2d3748 !important;">{generated_content}</div>
                </div>
                """, unsafe_allow_html=True)
                    
                    # Character count
                    char_count = len(generated_content)
                    color = "green" if char_count <= 1300 else "orange" if char_count <= 1500 else "red"
                    st.markdown(f"**Character count:** <span style='color: {color}'>{char_count}</span>", unsafe_allow_html=True)
                    
                    # Display persona evolution insights
                    if evolved_persona:
                        with st.expander("🧠 Your Evolved Voice Profile"):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.markdown("**Current Voice:**")
                                st.write(evolved_persona.get('current_voice', 'Developing...'))
                                
                                st.markdown("**Primary Tones:**")
                                st.write(", ".join(evolved_persona.get('primary_tones', ['Professional'])))
                                
                                st.markdown("**Writing Signature:**")
                                st.write(evolved_persona.get('writing_signature', 'Developing unique style...'))
                            
                            with col2:
                                st.markdown("**Success Patterns:**")
                                for pattern in evolved_persona.get('success_patterns', ['Building patterns...']):
                                    st.write(f"• {pattern}")
                                
                                st.markdown("**Engagement Strengths:**")
                                for strength in evolved_persona.get('engagement_strengths', ['Developing strengths...']):
                                    st.write(f"• {strength}")
                                
                                # Voice maturity metrics
                                voice_maturity = evolved_persona.get('voice_maturity_level', 0.5)
                                engagement_mastery = evolved_persona.get('engagement_mastery', 0.5)
                                
                                st.markdown("**Voice Development:**")
                                st.progress(voice_maturity, text=f"Voice Maturity: {voice_maturity:.1%}")
                                st.progress(engagement_mastery, text=f"Engagement Mastery: {engagement_mastery:.1%}")
                    
                    # Action buttons
                    st.markdown("### 🔄 Next Steps")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if st.button("📋 Copy to Clipboard"):
                            st.write("Content copied! (Use Ctrl+C to copy)")
                    
                    with col2:
                        if st.button("🔄 Generate Another"):
                            st.rerun()
                    
                    with col3:
                        if st.button("📊 Add Performance Data"):
                            st.session_state.show_performance_input = True
                    
                    # Performance data input (if user wants to add later)
                    if st.session_state.get('show_performance_input', False):
                        st.markdown("### 📈 Track This Post's Performance")
                        st.markdown("*Add engagement data to improve future content generation*")
                        
                        perf_col1, perf_col2, perf_col3, perf_col4 = st.columns(4)
                        
                        with perf_col1:
                            perf_likes = st.number_input("Likes", min_value=0, value=0, key="perf_likes")
                        with perf_col2:
                            perf_comments = st.number_input("Comments", min_value=0, value=0, key="perf_comments")
                        with perf_col3:
                            perf_shares = st.number_input("Shares", min_value=0, value=0, key="perf_shares")
                        with perf_col4:
                            perf_views = st.number_input("Views", min_value=0, value=0, key="perf_views")
                        
                        if st.button("💾 Save Performance Data"):
                            perf_data = {
                                'likes': perf_likes,
                                'comments': perf_comments,
                                'shares': perf_shares,
                                'views': perf_views
                            }
                            
                            # Update the post in memory with performance data
                            persona_system.add_user_post_to_memory(
                                user_id, 
                                generated_content, 
                                query, 
                                "Generated_Tracked", 
                                perf_data
                            )
                            
                            st.success("✅ Performance data saved! Your persona will evolve based on this feedback.")
                            st.session_state.show_performance_input = False
                            st.rerun()
                
                else:
                    st.error("Failed to generate content. Please try again.")
                    
            except Exception as e:
                st.error(f"Error during content generation: {str(e)}")
    
    with st.expander("🧠 Manage Your Context Memory", expanded=False):
        display_memory_feeder_interface(persona_system, user_id)

    # Context Summary
    display_context_summary(persona_system, user_id)
    
    # Evolution history section
    st.markdown("---")
    st.markdown("### 📚 Your Writing Evolution")

    # Get user's writing history
    try:
        user_history = persona_system.user_stm_collection.get(
            where={"user_id": {"$eq": user_id}}
        )
        
        if user_history['ids']:
            # Create DataFrame for history
            history_data = []
            for i, (doc, meta) in enumerate(zip(user_history['documents'], user_history['metadatas'])):
                history_data.append({
                    'Date': datetime.fromisoformat(meta['timestamp']).strftime('%Y-%m-%d'),
                    'Topic': meta.get('topic', 'Unknown'),
                    'Tone': meta.get('tone', 'Professional'),
                    'Engagement': f"{float(meta.get('engagement_score', 0.5)):.2f}",
                    'Post Type': meta.get('post_type', 'Generated'),
                    'Preview': doc[:100] + "..."
                })
            
            df = pd.DataFrame(history_data)
            st.dataframe(df, use_container_width=True)
            
            # Evolution insights
            if len(history_data) >= 3:
                st.markdown("#### 🎯 Your Evolution Insights")
                
                # Calculate trends
                engagement_scores = [float(meta.get('engagement_score', 0.5)) for meta in user_history['metadatas']]
                recent_avg = np.mean(engagement_scores[-3:]) if len(engagement_scores) >= 3 else 0
                overall_avg = np.mean(engagement_scores)
                
                insight_col1, insight_col2 = st.columns(2)
                
                with insight_col1:
                    trend = "📈 Improving" if recent_avg > overall_avg else "📊 Stable"
                    st.metric("Engagement Trend", trend, f"{recent_avg - overall_avg:+.2f}")
                
                with insight_col2:
                    dominant_tone = max(set([meta.get('tone', 'Professional') for meta in user_history['metadatas']]), 
                                      key=[meta.get('tone', 'Professional') for meta in user_history['metadatas']].count)
                    st.metric("Dominant Tone", dominant_tone)
        
        else:
            st.info("🌱 Start generating content to see your evolution journey!")

    except Exception as e:
        st.error(f"Error loading history: {str(e)}")
        
def display_memory_feeder_interface(persona_system, user_id):
    """Interface for adding user/company context"""
    
    st.markdown("### 🧠 Memory Feeder - Add Your Context")
    
    tab1, tab2, tab3 = st.tabs(["👤 Personal Context", "🏢 Company Info", "🏆 Achievements"])
    
    with tab1:
        st.markdown("#### Add Personal Context")
        
        context_type = st.selectbox(
            "Context Type",
            ["Personal", "Professional", "Experience", "Background", "Values"]
        )
        
        context_title = st.text_input("Title", placeholder="e.g., 'My Remote Work Philosophy'")
        context_content = st.text_area(
            "Content", 
            placeholder="Describe your experience, philosophy, or background...",
            height=100
        )
        
        context_tags = st.text_input(
            "Tags (comma-separated)", 
            placeholder="remote work, leadership, team management"
        )
        
        importance = st.slider("Importance Level", 0.0, 1.0, 0.5, 0.1)
        
        if st.button("💾 Save Personal Context"):
            if context_title and context_content:
                tags_list = [tag.strip() for tag in context_tags.split(",") if tag.strip()]
                context_id = persona_system.add_user_context(
                    user_id, context_type.lower(), context_title, 
                    context_content, tags_list, importance
                )
                st.success(f"✅ Personal context saved! ID: {context_id}")
            else:
                st.warning("Please fill in title and content")
    
    with tab2:
        st.markdown("#### Add Company Information")
        
        company_name = st.text_input("Company Name")
        info_type = st.selectbox(
            "Information Type",
            ["Culture", "Values", "News", "Achievements", "Products", "Industry", "Mission"]
        )
        
        company_title = st.text_input("Title", placeholder="e.g., 'Company Culture Initiative'")
        company_content = st.text_area(
            "Content",
            placeholder="Describe company culture, recent news, achievements...",
            height=100
        )
        
        relevance = st.slider("Relevance to Your Content", 0.0, 1.0, 0.5, 0.1)
        
        if st.button("💾 Save Company Info"):
            if company_name and company_title and company_content:
                company_id = persona_system.add_company_info(
                    user_id, company_name, info_type.lower(),
                    company_title, company_content, relevance
                )
                st.success(f"✅ Company info saved! ID: {company_id}")
            else:
                st.warning("Please fill in all fields")
    
    with tab3:
        st.markdown("#### Add Achievements & Experiences")
        
        achievement_type = st.selectbox(
            "Achievement Type",
            ["Project", "Award", "Milestone", "Learning", "Leadership", "Innovation"]
        )
        
        achievement_title = st.text_input("Title", placeholder="e.g., 'Led Digital Transformation Project'")
        achievement_desc = st.text_area(
            "Description",
            placeholder="Describe what you accomplished...",
            height=100
        )
        
        impact = st.text_area(
            "Impact (Optional)",
            placeholder="What was the result or impact?",
            height=68
        )
        
        date = st.text_input("Date (Optional)", placeholder="2024 or Q1 2024")
        skills = st.text_input(
            "Skills Used (comma-separated)", 
            placeholder="leadership, python, project management"
        )
        
        if st.button("💾 Save Achievement"):
            if achievement_title and achievement_desc:
                skills_list = [skill.strip() for skill in skills.split(",") if skill.strip()]
                achievement_id = persona_system.add_user_achievement(
                    user_id, achievement_type.lower(), achievement_title,
                    achievement_desc, impact, date, skills_list
                )
                st.success(f"✅ Achievement saved! ID: {achievement_id}")
            else:
                st.warning("Please fill in title and description")

def display_context_summary(persona_system, user_id):
    """Display summary of stored context"""
    
    st.markdown("### 📚 Your Stored Context")
    
    try:
        # Get all user context
        user_context = persona_system.user_context_collection.get(
            where={"user_id": {"$eq": user_id}}
        )
        
        company_context = persona_system.company_info_collection.get(
            where={"user_id": {"$eq": user_id}}
        )
        
        achievements = persona_system.user_achievements_collection.get(
            where={"user_id": {"$eq": user_id}}
        )
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Personal Context", len(user_context['ids']))
            
        with col2:
            st.metric("Company Info", len(company_context['ids']))
            
        with col3:
            st.metric("Achievements", len(achievements['ids']))
        
        # Show recent items
        if user_context['ids'] or company_context['ids'] or achievements['ids']:
            with st.expander("Recent Context Items"):
                
                if user_context['ids']:
                    st.markdown("**Personal Context:**")
                    for i, (doc, meta) in enumerate(zip(user_context['documents'][:3], user_context['metadatas'][:3])):
                        st.write(f"• {meta.get('title', 'Untitled')} ({meta.get('context_type', 'Unknown')})")
                
                if company_context['ids']:
                    st.markdown("**Company Info:**")
                    for i, (doc, meta) in enumerate(zip(company_context['documents'][:3], company_context['metadatas'][:3])):
                        st.write(f"• {meta.get('title', 'Untitled')} - {meta.get('company_name', 'Unknown Company')}")
                
                if achievements['ids']:
                    st.markdown("**Achievements:**")
                    for i, (doc, meta) in enumerate(zip(achievements['documents'][:3], achievements['metadatas'][:3])):
                        st.write(f"• {meta.get('title', 'Untitled')} ({meta.get('achievement_type', 'Unknown')})")
    
    except Exception as e:
        st.error(f"Error loading context summary: {e}")

def main():
    """Main function to run the Streamlit app"""
    st.set_page_config(
        page_title="LinkedIn Content Generator with Persona Evolution",
        page_icon="🚀",
        layout="wide"
    )
    
    # CSS styling
    st.markdown("""
    <style>
    .content-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #0066cc;
        color: #2d3748 !important;
    }
    /* Fix text visibility */
    .stMarkdown p, .stMarkdown div, .stText {
        color: #2d3748 !important;
    }
    /* Ensure generated content is visible */
    .generated-content {
        background-color: #f8f9fa !important;
        color: #2d3748 !important;
        padding: 20px;
        border-radius: 10px;
        border-left: 4px solid #0066cc;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "content_generation"
    
    # Navigation
    st.sidebar.title("🚀 Navigation")
    page = st.sidebar.selectbox(
        "Choose a page:",
        ["Content Generation", "Profile Setup", "Analytics"]
    )
    
    # Page routing
    if page == "Content Generation":
        display_enhanced_content_generation_page()
    elif page == "Profile Setup":
        st.title("👤 Profile Setup")
        st.info("Profile setup functionality would go here...")
    elif page == "Analytics":
        st.title("📊 Analytics Dashboard")
        st.info("Advanced analytics functionality would go here...")
if __name__ == "__main__":
    main()