from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy import text
from typing import Optional
from datetime import datetime
import secrets
import base64
import json

# Use the new auth module instead of inline auth
from app.auth import get_current_user_id

# Import database directly from main (after models are defined)
from app.main import get_db_context, engine

router = APIRouter()

# Dependency function for endpoints that need current user
def get_current_user(request: Request) -> dict:
    """Get current user ID for Depends() usage"""
    user_id = get_current_user_id(request)
    return {"id": user_id}

# ==================== CLIENT PORTAL ENDPOINTS ====================

@router.post("/client-view/generate")
async def generate_client_view_link(request: Request, data: dict):
    """Practitioner generates shareable link for client"""
    practitioner_id = get_current_user_id(request)
    family_member_id = data.get('family_member_id')
    
    with get_db_context() as db:
        # Verify member exists and belongs to practitioner
        result = db.execute(text("""
            SELECT id FROM family_members 
            WHERE id = :member_id AND user_id = :user_id
        """), {'member_id': family_member_id, 'user_id': str(practitioner_id)}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Client not found")
        
        token = secrets.token_urlsafe(32)
        
        # Deactivate old tokens
        db.execute(text("""
            UPDATE client_view_tokens 
            SET is_active = false 
            WHERE family_member_id = :member_id
        """), {'member_id': family_member_id})
        
        # Create new token
        db.execute(text("""
            INSERT INTO client_view_tokens (family_member_id, practitioner_id, token, is_active)
            VALUES (:member_id, :prac_id, :token, true)
        """), {
            'member_id': family_member_id,
            'prac_id': str(practitioner_id),
            'token': token
        })
        db.commit()
        
        link = f"https://treeoflife-vn25.onrender.com/api/client/view/{token}"
        
        return {"link": link, "token": token}


@router.get("/client-view/{token}")
async def get_client_view_data(token: str):
    """Load client's protocol data via token (no auth required)"""
    
    with engine.connect() as conn:
        # Verify token
        result = conn.execute(text("""
            SELECT family_member_id, practitioner_id, is_active
            FROM client_view_tokens
            WHERE token = :token
        """), {'token': token}).fetchone()
        
        if not result or not result[2]:
            raise HTTPException(status_code=404, detail="Invalid or expired link")
        
        family_member_id = result[0]
        practitioner_id = result[1]
        
        # Update last accessed time
        conn.execute(text("""
            UPDATE client_view_tokens
            SET last_accessed = CURRENT_TIMESTAMP
            WHERE token = :token
        """), {'token': token})
        conn.commit()
        
        # Get member info
        member = conn.execute(text("""
            SELECT name FROM family_members WHERE id = :id
        """), {'id': family_member_id}).fetchone()
        
        # Get practitioner info
        practitioner = conn.execute(text("""
            SELECT full_name, email FROM users WHERE id = :id
        """), {'id': str(practitioner_id)}).fetchone()
        
        # Get active protocol assignment
        assignment = conn.execute(text("""
            SELECT id, protocol_id, current_week, completion_percentage
            FROM client_protocols
            WHERE client_id = :client_id AND status = 'active'
            LIMIT 1
        """), {'client_id': family_member_id}).fetchone()
        
        if not assignment:
            return {
                "client_name": member[0],
                "practitioner_name": practitioner[0] or practitioner[1],
                "protocol": None
            }
        
        # Get full protocol data
        protocol = conn.execute(text("""
            SELECT 
                name, description, traditions, duration_weeks,
                supplements, exercises, lifestyle_changes, nutrition,
                sleep, stress_management, weekly_notes
            FROM protocols
            WHERE id = :id
        """), {'id': assignment[1]}).fetchone()
        
        # Get recent compliance logs
        compliance = conn.execute(text("""
            SELECT week_number, compliance_score
            FROM compliance_logs
            WHERE client_protocol_id = :id
            ORDER BY week_number DESC
            LIMIT 4
        """), {'id': assignment[0]}).fetchall()
        
        # Build supplements list
        supplements_list = []
        
        # Add supplements
        if protocol[4]:  # supplements
            supp_data = protocol[4]
            # Handle if it's a JSON string
            if isinstance(supp_data, str):
                try:
                    supp_data = json.loads(supp_data)
                except:
                    pass
            
            if isinstance(supp_data, dict):
                for name, instructions in supp_data.items():
                    if instructions and str(instructions).strip():
                        supplements_list.append(f"{name} - {instructions}")
                    else:
                        supplements_list.append(name)
            elif isinstance(supp_data, list):
                # Handle list of structured objects
                for item in supp_data:
                    if isinstance(item, dict):
                        # Build readable string from structured data
                        parts = [item.get('name', 'Unknown')]
                        
                        if item.get('dosage'):
                            parts.append(item['dosage'])
                        if item.get('frequency'):
                            parts.append(item['frequency'].lower())
                        if item.get('timing'):
                            parts.append(f"({item['timing'].lower()})")
                        if item.get('with_food'):
                            parts.append(item['with_food'].lower())
                        if item.get('instructions'):
                            parts.append(f"- {item['instructions']}")
                        if item.get('notes') and item['notes'].strip():
                            parts.append(f"Note: {item['notes']}")
                        
                        supplements_list.append(' '.join(parts))
                    elif isinstance(item, str):
                        supplements_list.append(item)
        
        # Build exercises list (separate from supplements)
        exercises_list = []
        
        # Add exercises
        if protocol[5]:  # exercises
            ex_data = protocol[5]
            # Handle if it's a JSON string
            if isinstance(ex_data, str):
                try:
                    ex_data = json.loads(ex_data)
                except:
                    pass
            
            if isinstance(ex_data, dict):
                for name, instructions in ex_data.items():
                    if instructions and str(instructions).strip():
                        exercises_list.append(f"{name} - {instructions}")
                    else:
                        exercises_list.append(name)
            elif isinstance(ex_data, list):
                # Handle list of structured exercise objects
                for item in ex_data:
                    if isinstance(item, dict):
                        # Build readable string from structured data
                        parts = [item.get('name', 'Unknown exercise')]
                        
                        if item.get('duration'):
                            parts.append(f"{item['duration']} minutes")
                        if item.get('frequency'):
                            freq = item['frequency']
                            if freq == '1':
                                parts.append('daily')
                            else:
                                parts.append(f"{freq}x per week")
                        if item.get('intensity'):
                            parts.append(f"({item['intensity'].lower()} intensity)")
                        if item.get('instructions') and item['instructions'].strip():
                            parts.append(f"- {item['instructions']}")
                        
                        exercises_list.append(' '.join(parts))
                    elif isinstance(item, str):
                        exercises_list.append(item)
        
        # Build lifestyle changes list (habits only, not nutrition/sleep/stress)
        lifestyle_changes = []
        
        # Add lifestyle_changes field (just the habits)
        if protocol[6]:  # lifestyle_changes
            lc_data = protocol[6]
            # Handle if it's a JSON string
            if isinstance(lc_data, str):
                try:
                    lc_data = json.loads(lc_data)
                except:
                    pass
            
            if isinstance(lc_data, dict):
                for key, value in lc_data.items():
                    if isinstance(value, dict):
                        # Extract all key-value pairs from nested dict
                        for k, v in value.items():
                            if v and str(v).strip():
                                lifestyle_changes.append(f"{key.title()} - {k}: {v}")
                    elif isinstance(value, list):
                        if value:  # Only add if list is not empty
                            lifestyle_changes.append(f"{key.title()}: {', '.join(str(v) for v in value)}")
                    else:
                        if value and str(value).strip():
                            lifestyle_changes.append(f"{key.title()}: {value}")
            elif isinstance(lc_data, list):
                # Handle list of mixed strings and objects
                for item in lc_data:
                    if isinstance(item, dict):
                        # Build readable string from structured lifestyle change
                        parts = []
                        
                        if item.get('title'):
                            parts.append(f"🎯 {item['title']}")
                        if item.get('category'):
                            parts.append(f"({item['category']})")
                        if item.get('frequency'):
                            parts.append(f"- {item['frequency']}")
                        if item.get('description'):
                            parts.append(f": {item['description']}")
                        
                        if parts:
                            lifestyle_changes.append(' '.join(parts))
                    elif isinstance(item, str):
                        # Add emoji to Stress Management if it doesn't have one
                        if item.startswith('Stress Management') and not item.startswith('🧘'):
                            lifestyle_changes.append(f"🧘 {item}")
                        else:
                            lifestyle_changes.append(item)
        
        # Build nutrition list
        nutrition_list = []
        
        # Add nutrition
        if protocol[7]:  # nutrition
            nut_data = protocol[7]
            if protocol[7]:  # nutrition

            nut_data = protocol[7]
            print(f"NUTRITION DEBUG - Type: {type(nut_data)}, Value: {nut_data}")
          
            
            # Handle if it's a JSON string
            if isinstance(nut_data, str):
                try:
                    nut_data = json.loads(nut_data)
                    print(f"Parsed nutrition data: {nut_data}")
                except:
                    print("Failed to parse as JSON")
                    pass
            
            if isinstance(nut_data, dict):
            
            if isinstance(nut_data, dict):
                # Add dietary approach
                if nut_data.get('dietary_approach') and str(nut_data['dietary_approach']).strip():
                    nutrition_list.append(f"🥗 Dietary Approach: {nut_data['dietary_approach']}")
                
                # Add foods to include (handle both string and array)
                if nut_data.get('foods_to_include'):
                    foods = nut_data['foods_to_include']
                    if isinstance(foods, list) and foods:
                        foods_str = ', '.join(str(f).strip() for f in foods if f and str(f).strip())
                        if foods_str:
                            nutrition_list.append(f"✅ Foods to Include: {foods_str}")
                    elif isinstance(foods, str) and foods.strip():
                        # Split by common delimiters if it's a string
                        foods_list = [f.strip() for f in foods.replace(',', '\n').replace(';', '\n').split('\n') if f.strip()]
                        if foods_list:
                            nutrition_list.append(f"✅ Foods to Include: {', '.join(foods_list)}")
                
                # Add foods to avoid (handle both string and array)
                if nut_data.get('foods_to_avoid'):
                    foods = nut_data['foods_to_avoid']
                    if isinstance(foods, list) and foods:
                        foods_str = ', '.join(str(f).strip() for f in foods if f and str(f).strip())
                        if foods_str:
                            nutrition_list.append(f"⛔ Foods to Avoid: {foods_str}")
                    elif isinstance(foods, str) and foods.strip():
                        # Split by common delimiters if it's a string
                        foods_list = [f.strip() for f in foods.replace(',', '\n').replace(';', '\n').split('\n') if f.strip()]
                        if foods_list:
                            nutrition_list.append(f"⛔ Foods to Avoid: {', '.join(foods_list)}")
                
                # Add meal timing/structure
                if nut_data.get('meal_timing') and str(nut_data['meal_timing']).strip():
                    nutrition_list.append(f"⏰ Meal Timing: {nut_data['meal_timing']}")
                elif nut_data.get('meal_structure') and str(nut_data['meal_structure']).strip():
                    nutrition_list.append(f"⏰ Meal Structure: {nut_data['meal_structure']}")
                
                # Add hydration goals
                if nut_data.get('hydration') and str(nut_data['hydration']).strip():
                    nutrition_list.append(f"💧 Hydration: {nut_data['hydration']}")
                elif nut_data.get('hydration_goals') and str(nut_data['hydration_goals']).strip():
                    nutrition_list.append(f"💧 Hydration: {nut_data['hydration_goals']}")
                
                # Add daily calories if present
                if nut_data.get('daily_calories') and str(nut_data['daily_calories']).strip():
                    nutrition_list.append(f"📊 Daily Calories: {nut_data['daily_calories']}")
                    
            elif isinstance(nut_data, str) and nut_data.strip():
                nutrition_list.append(f"🥗 Nutrition: {nut_data}")
        
        # Add sleep to lifestyle
        if protocol[8]:  # sleep
            sleep_data = protocol[8]
            # Handle if it's a JSON string
            if isinstance(sleep_data, str):
                try:
                    sleep_data = json.loads(sleep_data)
                except:
                    pass
            
            if isinstance(sleep_data, dict):
                sleep_items = []
                
                if sleep_data.get('bedtime') and str(sleep_data['bedtime']).strip():
                    sleep_items.append(f"Bedtime: {sleep_data['bedtime']}")
                if sleep_data.get('target_hours') and str(sleep_data['target_hours']).strip():
                    sleep_items.append(f"Target: {sleep_data['target_hours']} hours")
                if sleep_data.get('notes') and str(sleep_data['notes']).strip():
                    sleep_items.append(f"{sleep_data['notes']}")
                
                # Combine all sleep items into one line
                if sleep_items:
                    lifestyle_changes.append(f"😴 Sleep: {' | '.join(sleep_items)}")
                    
            elif isinstance(sleep_data, str) and sleep_data.strip():
                lifestyle_changes.append(f"😴 Sleep: {sleep_data}")
        
        # Add stress management (only if not already in lifestyle_changes)
        if protocol[9]:  # stress_management
            stress_text = str(protocol[9]).strip() if protocol[9] else ""
            if stress_text:
                # Check if already added via lifestyle_changes
                already_added = any('Stress Management' in str(item) for item in lifestyle_changes)
                if not already_added:
                    lifestyle_changes.append(f"🧘 Stress Management: {stress_text}")
        
        # Build timeline list  
        timeline_list = []
        
        # Add weekly notes - extract and display timeline
        if protocol[10]:  # weekly_notes
            notes_data = protocol[10]
            
            # DEBUG: Log raw data
            print(f"\n=== WEEKLY NOTES DEBUG ===")
            print(f"Type: {type(notes_data)}")
            print(f"Content: {notes_data}")
            
            # Handle if it's a JSON string
            if isinstance(notes_data, str):
                try:
                    notes_data = json.loads(notes_data)
                    print(f"Parsed to: {notes_data}")
                except:
                    print("Failed to parse as JSON")
                    pass
            
            if isinstance(notes_data, dict):
                current_week_num = assignment[2]  # current_week
                
                # Try to extract notes for all weeks with flexible key matching
                week_notes = {}
                for key, value in notes_data.items():
                    if value and str(value).strip():
                        week_num = None
                        key_lower = str(key).lower()
                        
                        # Try various key formats
                        if 'week 1' in key_lower or 'week1' in key_lower or key == '1':
                            week_num = 1
                        elif 'week 2' in key_lower or 'week2' in key_lower or key == '2':
                            week_num = 2
                        elif 'week 3' in key_lower or 'week3' in key_lower or key == '3':
                            week_num = 3
                        elif 'week 4' in key_lower or 'week4' in key_lower or key == '4':
                            week_num = 4
                        elif 'week_1' in key_lower:
                            week_num = 1
                        elif 'week_2' in key_lower:
                            week_num = 2
                        elif 'week_3' in key_lower:
                            week_num = 3
                        elif 'week_4' in key_lower:
                            week_num = 4
                        elif key.isdigit():
                            week_num = int(key)
                        
                        if week_num:
                            week_notes[week_num] = str(value).strip()
                            print(f"Extracted Week {week_num}: {value}")
                
                print(f"Total weeks extracted: {len(week_notes)}")
                
                # Add current week's focus at the top
                if current_week_num in week_notes:
                    timeline_list.append(f"⭐ This Week's Focus: {week_notes[current_week_num]}")
                    print(f"Added current week focus: {week_notes[current_week_num]}")
                else:
                    print(f"WARNING: No note found for current week {current_week_num}")
                
                # Add full timeline preview
                if len(week_notes) > 0:
                    timeline_items = []
                    for week_num in sorted(week_notes.keys()):
                        if week_num == current_week_num:
                            timeline_items.append(f"→ Week {week_num}: {week_notes[week_num]} ⬅ You are here")
                        else:
                            timeline_items.append(f"Week {week_num}: {week_notes[week_num]}")
                    
                    if timeline_items:
                        # Add as separate items for better readability
                        timeline_list.append("📅 ─── Protocol Timeline ───")
                        for item in timeline_items:
                            timeline_list.append(f"   {item}")
                        
            elif isinstance(notes_data, str) and notes_data.strip():
                # If weekly_notes is just a string, use it as the focus
                timeline_list.append(f"⭐ This Week's Focus: {notes_data}")
                print(f"Added string note: {notes_data}")
            
            print("=== END WEEKLY NOTES DEBUG ===\n")
        
        return {
            "client_name": member[0],
            "practitioner_name": practitioner[0] or practitioner[1],
            "protocol": {
                "name": protocol[0],
                "current_week": assignment[2],
                "total_weeks": protocol[3],
                "completion_percentage": assignment[3],
                
                # Format as current_phase for frontend compatibility
                "current_phase": {
                    "title": f"Week {assignment[2]} - {protocol[0]}",
                    "instructions": protocol[1] or "",  # description
                    "supplements": supplements_list,
                    "nutrition": nutrition_list,
                    "exercises": exercises_list,
                    "lifestyle": lifestyle_changes,
                    "timeline": timeline_list
                },
                
                "recent_compliance": [{
                    "week": log[0],
                    "score": log[1]
                } for log in compliance]
            }
        }


@router.post("/client-view/{token}/compliance")
async def mark_client_compliance(token: str, data: dict):
    """Client marks items as complete with detailed breakdown"""
    
    compliance_score = data.get('compliance_score', 100)
    completed_items = data.get('completed_items', [])
    incomplete_items = data.get('incomplete_items', [])
    total_items = data.get('total_items', 0)
    
    # Create detailed notes with breakdown
    compliance_details = {
        'total_items': total_items,
        'completed_count': len(completed_items),
        'incomplete_count': len(incomplete_items),
        'completed_items': completed_items,
        'incomplete_items': incomplete_items
    }
    
    notes_text = f"Self-reported via client view. {len(completed_items)}/{total_items} items completed."
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT family_member_id FROM client_view_tokens
            WHERE token = :token AND is_active = true
        """), {'token': token}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Invalid link")
        
        family_member_id = result[0]
        
        assignment = conn.execute(text("""
            SELECT id, current_week FROM client_protocols
            WHERE client_id = :client_id AND status = 'active'
            LIMIT 1
        """), {'client_id': family_member_id}).fetchone()
        
        if not assignment:
            raise HTTPException(status_code=404, detail="No active protocol")
        
        # Check if compliance_logs table has compliance_details column
        # If not, store in notes as JSON string
        try:
            conn.execute(text("""
                INSERT INTO compliance_logs 
                (client_protocol_id, week_number, compliance_score, compliance_details, notes, logged_at)
                VALUES (:protocol_id, :week, :score, :details::jsonb, :notes, CURRENT_TIMESTAMP)
            """), {
                'protocol_id': assignment[0],
                'week': assignment[1],
                'score': compliance_score,
                'details': json.dumps(compliance_details),
                'notes': notes_text
            })
        except Exception as e:
            # Fallback: store details in notes field if compliance_details column doesn't exist
            conn.execute(text("""
                INSERT INTO compliance_logs 
                (client_protocol_id, week_number, compliance_score, notes, logged_at)
                VALUES (:protocol_id, :week, :score, :notes, CURRENT_TIMESTAMP)
            """), {
                'protocol_id': assignment[0],
                'week': assignment[1],
                'score': compliance_score,
                'notes': f"{notes_text}\n\nDetails: {json.dumps(compliance_details)}"
            })
        
        conn.commit()
        
        return {"success": True, "details_saved": True}


@router.get("/pro/client/{member_id}/compliance-details")
async def get_client_compliance_details(member_id: int, current_user: dict = Depends(get_current_user)):
    """Get detailed compliance breakdown for a specific client"""
    
    try:
        with engine.connect() as conn:
            # Verify client belongs to this practitioner
            member = conn.execute(text("""
                SELECT name FROM family_members
                WHERE id = :member_id AND user_id = :user_id
            """), {'member_id': member_id, 'user_id': current_user['id']}).fetchone()
            
            if not member:
                raise HTTPException(status_code=404, detail="Client not found")
            
            # Get active protocol (only use duration_weeks)
            protocol = conn.execute(text("""
                SELECT cp.id, cp.current_week, p.name as protocol_name, 
                       p.duration_weeks as total_weeks
                FROM client_protocols cp
                JOIN protocols p ON cp.protocol_id = p.id
                WHERE cp.client_id = :client_id AND cp.status = 'active'
                LIMIT 1
            """), {'client_id': member_id}).fetchone()
            
            if not protocol:
                return {
                    "client_name": member[0],
                    "has_protocol": False,
                    "has_data": False,
                    "message": "No active protocol",
                    "completed_items": [],
                    "incomplete_items": [],
                    "category_breakdown": {}
                }
            
            # Get most recent compliance log with details
            compliance_log = conn.execute(text("""
                SELECT 
                    week_number,
                    compliance_score,
                    compliance_details,
                    notes,
                    logged_at
                FROM compliance_logs
                WHERE client_protocol_id = :protocol_id
                ORDER BY logged_at DESC
                LIMIT 1
            """), {'protocol_id': protocol[0]}).fetchone()
            
            if not compliance_log:
                return {
                    "client_name": member[0],
                    "protocol_name": protocol[2],
                    "current_week": protocol[1],
                    "total_weeks": protocol[3],
                    "has_data": False,
                    "message": "No compliance data yet",
                    "completed_items": [],
                    "incomplete_items": [],
                    "category_breakdown": {}
                }
            
            # Parse compliance details
            print(f"🔍 Raw compliance_log data: {compliance_log}")
            compliance_details = None
            if compliance_log[2]:  # compliance_details column exists
                try:
                    print(f"🔍 Parsing compliance_details from column: {compliance_log[2]}")
                    if isinstance(compliance_log[2], str):
                        compliance_details = json.loads(compliance_log[2])
                    else:
                        compliance_details = compliance_log[2]
                    print(f"✅ Parsed compliance_details: {compliance_details}")
                except Exception as e:
                    print(f"❌ Error parsing compliance_details: {e}")
                    import traceback
                    traceback.print_exc()
            
            # If no compliance_details column, try to extract from notes
            if not compliance_details and compliance_log[3]:
                try:
                    if "Details:" in compliance_log[3]:
                        details_str = compliance_log[3].split("Details:")[1].strip()
                        compliance_details = json.loads(details_str)
                except Exception as e:
                    print(f"❌ Error parsing notes: {e}")
            
            # Calculate category breakdowns if we have detailed data
            category_breakdown = {}
            completed_items = []
            incomplete_items = []
            
            print(f"🔍 compliance_details type: {type(compliance_details)}")
            print(f"🔍 compliance_details value: {compliance_details}")
            
            if compliance_details:
                try:
                    completed_items = compliance_details.get('completed_items', [])
                    incomplete_items = compliance_details.get('incomplete_items', [])
                    print(f"🔍 completed_items: {completed_items}")
                    print(f"🔍 incomplete_items: {incomplete_items}")
                    
                    if completed_items or incomplete_items:
                        # Count by category
                        categories = {
                            'supplements': {'completed': 0, 'total': 0},
                            'nutrition': {'completed': 0, 'total': 0},
                            'exercises': {'completed': 0, 'total': 0},
                            'lifestyle': {'completed': 0, 'total': 0},
                            'timeline': {'completed': 0, 'total': 0}
                        }
                        
                        print(f"🔍 Processing {len(completed_items)} completed items")
                        for item in completed_items:
                            print(f"🔍 Completed item: {item}, type: {type(item)}")
                            if isinstance(item, dict) and 'id' in item:
                                category = item['id'].split('-')[0]
                                if category in categories:
                                    categories[category]['completed'] += 1
                                    categories[category]['total'] += 1
                        
                        print(f"🔍 Processing {len(incomplete_items)} incomplete items")
                        for item in incomplete_items:
                            print(f"🔍 Incomplete item: {item}, type: {type(item)}")
                            if isinstance(item, dict) and 'id' in item:
                                category = item['id'].split('-')[0]
                                if category in categories:
                                    categories[category]['total'] += 1
                        
                        # Calculate percentages
                        for cat, data in categories.items():
                            if data['total'] > 0:
                                percentage = round((data['completed'] / data['total']) * 100)
                                category_breakdown[cat] = {
                                    'completed': data['completed'],
                                    'total': data['total'],
                                    'percentage': percentage
                                }
                        
                        print(f"✅ Final category_breakdown: {category_breakdown}")
                except Exception as e:
                    print(f"❌ Error processing compliance data: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Handle logged_at - might be datetime or string
            logged_at_str = None
            if compliance_log[4]:
                if hasattr(compliance_log[4], 'isoformat'):
                    logged_at_str = compliance_log[4].isoformat()
                else:
                    logged_at_str = str(compliance_log[4])
            
            return {
                "client_name": member[0],
                "protocol_name": protocol[2],
                "current_week": protocol[1],
                "total_weeks": protocol[3],
                "has_data": True,
                "compliance_score": compliance_log[1],
                "week_number": compliance_log[0],
                "logged_at": logged_at_str,
                "completed_items": completed_items,
                "incomplete_items": incomplete_items,
                "total_items": compliance_details.get('total_items', 0) if compliance_details else 0,
                "category_breakdown": category_breakdown
            }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in compliance-details: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error loading compliance: {str(e)}")


@router.post("/client-view/{token}/message")
async def send_client_message(
    token: str,
    message: str = Form(...),
    image: Optional[UploadFile] = File(None)
):
    """Client sends message to practitioner with optional image"""
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT family_member_id, practitioner_id
            FROM client_view_tokens
            WHERE token = :token AND is_active = true
        """), {'token': token}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Invalid link")
        
        family_member_id = result[0]
        practitioner_id = result[1]
        
        image_data = None
        if image:
            image_content = await image.read()
            
            if not image.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail="Only image files allowed")
            
            if len(image_content) > 5 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="Image too large (max 5MB)")
            
            image_base64 = base64.b64encode(image_content).decode('utf-8')
            image_data = f"data:{image.content_type};base64,{image_base64}"
        
        conn.execute(text("""
            INSERT INTO client_messages 
            (family_member_id, practitioner_id, message_text, image_base64)
            VALUES (:member_id, :prac_id, :message, :image)
        """), {
            'member_id': family_member_id,
            'prac_id': str(practitioner_id),
            'message': message,
            'image': image_data
        })
        conn.commit()
        
        return {"success": True, "message": "Message sent to your practitioner"}


@router.get("/client-view/{token}/replies")
async def get_client_replies(token: str):
    """Client checks for practitioner replies"""
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT family_member_id
            FROM client_view_tokens
            WHERE token = :token AND is_active = true
        """), {'token': token}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Invalid link")
        
        family_member_id = result[0]
        
        results = conn.execute(text("""
            SELECT 
                message_text, reply_text, replied_at, created_at
            FROM client_messages
            WHERE family_member_id = :member_id
              AND reply_text IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 10
        """), {'member_id': family_member_id}).fetchall()
        
        replies = [{
            'your_question': row[0],
            'practitioner_reply': row[1],
            'replied_at': row[2].isoformat() if row[2] else None,
            'asked_at': row[3].isoformat()
        } for row in results]
        
        return {"replies": replies}


@router.get("/client/view/{token}", response_class=HTMLResponse)
async def serve_client_view_page(token: str):
    """Serve the client view HTML page"""
    html_path = "app/templates/client_view.html"
    
    try:
        with open(html_path, 'r') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Client view page not found")


@router.post("/client-view/{token}/submit-compliance")
async def submit_client_compliance(token: str, data: dict):
    """Client submits their weekly compliance checklist"""
    
    with engine.connect() as conn:
        # Verify token
        result = conn.execute(text("""
            SELECT family_member_id, practitioner_id
            FROM client_view_tokens
            WHERE token = :token AND is_active = true
        """), {'token': token}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Invalid link")
        
        family_member_id = result[0]
        
        # Get active protocol
        protocol = conn.execute(text("""
            SELECT id, current_week
            FROM client_protocols
            WHERE client_id = :client_id AND status = 'active'
            LIMIT 1
        """), {'client_id': family_member_id}).fetchone()
        
        if not protocol:
            raise HTTPException(status_code=404, detail="No active protocol")
        
        protocol_id = protocol[0]
        current_week = protocol[1]
        
        # Extract compliance data
        completed_items = data.get('completed_items', [])
        incomplete_items = data.get('incomplete_items', [])
        total_items = data.get('total_items', 0)
        
        # Calculate compliance score
        compliance_score = 0
        if total_items > 0:
            compliance_score = round((len(completed_items) / total_items) * 100)
        
        # Store compliance details as JSON
        compliance_details = {
            'completed_items': completed_items,
            'incomplete_items': incomplete_items,
            'total_items': total_items,
            'submitted_at': datetime.now().isoformat()
        }
        
        # Check if compliance log already exists for this week
        existing = conn.execute(text("""
            SELECT id FROM compliance_logs
            WHERE client_protocol_id = :protocol_id AND week_number = :week
        """), {'protocol_id': protocol_id, 'week': current_week}).fetchone()
        
        if existing:
            # Update existing log
            conn.execute(text("""
                UPDATE compliance_logs
                SET compliance_score = :score,
                    compliance_details = :details,
                    logged_at = CURRENT_TIMESTAMP
                WHERE id = :id
            """), {
                'score': compliance_score,
                'details': json.dumps(compliance_details),
                'id': existing[0]
            })
        else:
            # Create new log
            conn.execute(text("""
                INSERT INTO compliance_logs 
                (client_protocol_id, week_number, compliance_score, compliance_details, logged_at)
                VALUES (:protocol_id, :week, :score, :details, CURRENT_TIMESTAMP)
            """), {
                'protocol_id': protocol_id,
                'week': current_week,
                'score': compliance_score,
                'details': json.dumps(compliance_details)
            })
        
        # Update protocol completion percentage
        conn.execute(text("""
            UPDATE client_protocols
            SET completion_percentage = :percentage
            WHERE id = :protocol_id
        """), {
            'percentage': compliance_score,
            'protocol_id': protocol_id
        })
        
        conn.commit()
        
        return {
            "success": True,
            "compliance_score": compliance_score,
            "week_number": current_week,
            "message": f"Week {current_week} compliance saved: {compliance_score}%"
        }

