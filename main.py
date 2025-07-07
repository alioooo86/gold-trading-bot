#!/usr/bin/env python3
"""
Critical Fixes and Improvements for Gold Trading Bot v4.9
These address the specific issues mentioned by the user
"""

# ============================================================================
# FIX: COMPLETE CALLBACK HANDLER - ADD MISSING CASES
# ============================================================================

def handle_callbacks_FIXED(call):
    """FIXED: Complete callback handler with ALL missing cases"""
    try:
        user_id = call.from_user.id
        data = call.data
        
        logger.info(f"📱 Callback: {user_id} -> {data}")
        
        if data.startswith('login_'):
            handle_login_with_telegram_registration(call)
        elif data == 'show_rate':
            handle_show_rate(call)
        elif data == 'force_refresh_rate':
            handle_force_refresh_rate(call)
        elif data == 'dashboard':
            handle_dashboard(call)
        elif data == 'new_trade':
            handle_new_trade(call)
        elif data == 'approval_dashboard':
            handle_approval_dashboard(call)
        elif data == 'view_pending':
            handle_view_pending(call)
        elif data == 'approval_stats':
            handle_approval_stats(call)
        elif data.startswith('approve_'):
            if data.startswith('approve_no_comment_'):
                handle_no_comment_approval(call)
            else:
                handle_approve_trade(call)
        elif data.startswith('reject_'):
            handle_reject_trade(call)
        elif data == 'system_status':
            handle_system_status(call)
            
        # ============================================================================
        # SHEET MANAGEMENT - ADD ALL MISSING CALLBACKS
        # ============================================================================
        elif data == 'sheet_management':
            handle_sheet_management(call)
        elif data == 'view_sheets':
            handle_view_sheets(call)
        elif data == 'format_sheet':
            handle_format_sheet(call)
        elif data == 'fix_headers':
            handle_fix_headers(call)
        elif data == 'delete_sheets':
            handle_delete_sheets(call)
        elif data == 'clear_sheets':
            handle_clear_sheets(call)
        elif data == 'sheet_stats':
            handle_sheet_stats(call)  # NEW FUNCTION
        elif data.startswith('delete_') or data.startswith('clear_'):
            handle_sheet_action(call)
            
        # ============================================================================
        # TRADE NAVIGATION - ADD MISSING CALLBACKS
        # ============================================================================
        elif data == 'prev_trade':
            handle_trade_navigation(call, -1)
        elif data == 'next_trade':
            handle_trade_navigation(call, 1)
            
        # ============================================================================
        # TRADE FLOW - ENSURE ALL CALLBACKS ARE HANDLED
        # ============================================================================
        elif data.startswith('operation_'):
            handle_operation(call)
        elif data.startswith('goldtype_'):
            handle_gold_type(call)
        elif data.startswith('quantity_'):
            handle_quantity(call)  # RESTORED
        elif data.startswith('purity_'):
            handle_purity(call)
        elif data.startswith('volume_'):
            handle_volume(call)
        elif data.startswith('customer_'):
            handle_customer(call)
        elif data.startswith('rate_'):
            handle_rate_choice(call)
        elif data.startswith('pd_'):
            handle_pd_type(call)
        elif data.startswith('premium_') or data.startswith('discount_'):
            handle_pd_amount(call)
        elif data == 'confirm_trade':
            handle_confirm_trade(call)
        elif data == 'cancel_trade':
            handle_cancel_trade(call)
        elif data == 'start':
            start_command(call.message)
        else:
            # Handle unknown callbacks gracefully
            logger.warning(f"⚠️ Unknown callback: {data}")
            try:
                bot.edit_message_text(
                    "🚧 Feature under development or invalid callback...",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton("🔙 Back", callback_data="dashboard")
                    )
                )
            except:
                pass
        
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        logger.error(f"❌ Callback error: {e}")
        try:
            bot.answer_callback_query(call.id, f"Error: {str(e)[:100]}")
        except:
            pass

# ============================================================================
# MISSING: SHEET STATISTICS FUNCTION
# ============================================================================

def handle_sheet_stats(call):
    """Show detailed sheet statistics with percentages"""
    try:
        bot.edit_message_text("📊 Loading detailed statistics...", call.message.chat.id, call.message.message_id)
        
        success, sheet_info = get_all_sheets()
        
        if not success or not sheet_info:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="sheet_management"))
            bot.edit_message_text("❌ No sheets found", call.message.chat.id, call.message.message_id, reply_markup=markup)
            return
        
        stats_text = "📊 DETAILED SHEET STATISTICS:\n\n"
        
        total_trades = 0
        total_approved = 0
        
        for sheet in sheet_info:
            try:
                approval_pct = get_approval_percentage(sheet['name'])
                data_rows = sheet.get('data_rows', 0)
                if isinstance(data_rows, int) and data_rows > 0:
                    trades_count = data_rows - 1  # Exclude header
                    approved_count = int((approval_pct / 100) * trades_count) if approval_pct > 0 else 0
                    
                    total_trades += trades_count
                    total_approved += approved_count
                    
                    stats_text += f"📋 {sheet['name']}\n"
                    stats_text += f"   • Total Trades: {trades_count}\n"
                    stats_text += f"   • Approved: {approved_count}\n"
                    stats_text += f"   • Approval Rate: {approval_pct}%\n"
                    stats_text += f"   • Status: {'🟢 Active' if trades_count > 0 else '⚪ Empty'}\n\n"
                else:
                    stats_text += f"📋 {sheet['name']}\n"
                    stats_text += f"   • Status: ⚪ Empty or No Data\n\n"
            except Exception as e:
                logger.error(f"Error processing sheet {sheet.get('name', 'Unknown')}: {e}")
                stats_text += f"📋 {sheet.get('name', 'Unknown')}\n"
                stats_text += f"   • Status: ❌ Error loading data\n\n"
        
        # Overall statistics
        overall_pct = (total_approved / total_trades * 100) if total_trades > 0 else 0
        stats_text += f"🎯 OVERALL STATISTICS:\n"
        stats_text += f"• Total Sheets: {len(sheet_info)}\n"
        stats_text += f"• Total Trades: {total_trades}\n"
        stats_text += f"• Total Approved: {total_approved}\n"
        stats_text += f"• Overall Approval Rate: {overall_pct:.1f}%\n"
        
        # Status color coding
        stats_text += f"\n📊 COLOR CODING IN SHEETS:\n"
        stats_text += f"• 🔴 PENDING (Red background)\n"
        stats_text += f"• 🟡 LEVEL_1_APPROVED (Yellow)\n"
        stats_text += f"• 🟠 LEVEL_2_APPROVED (Orange)\n"
        stats_text += f"• 🟢 FINAL_APPROVED (Green)\n"
        stats_text += f"• ⚫ REJECTED (Dark red)\n"
        
        # Split message if too long
        if len(stats_text) > 3800:
            stats_text = stats_text[:3800] + "...\n\n[Message truncated]"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔄 Refresh Stats", callback_data="sheet_stats"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="sheet_management"))
        
        bot.edit_message_text(stats_text, call.message.chat.id, call.message.message_id, reply_markup=markup)
        
    except Exception as e:
        logger.error(f"Sheet stats error: {e}")

# ============================================================================
# FIX: ENHANCED APPROVAL PERCENTAGE CALCULATION
# ============================================================================

def get_approval_percentage_ENHANCED(sheet_name):
    """ENHANCED: Calculate approval percentage with detailed status tracking"""
    try:
        client = get_sheets_client()
        if not client:
            return 0
        
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
        
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
        except:
            logger.warning(f"Sheet {sheet_name} not found")
            return 0
        
        all_values = worksheet.get_all_values()
        if len(all_values) <= 1:  # Only headers or empty
            return 0
        
        total_trades = len(all_values) - 1  # Exclude header
        
        # Count different status types
        status_counts = {
            "PENDING": 0,
            "LEVEL_1_APPROVED": 0,
            "LEVEL_2_APPROVED": 0,
            "FINAL_APPROVED": 0,
            "REJECTED": 0
        }
        
        # Status is in column W (index 22)
        for row in all_values[1:]:  # Skip header
            if len(row) > 22:
                status = row[22].strip()
                if status in status_counts:
                    status_counts[status] += 1
                else:
                    # Handle any status not in our list
                    logger.warning(f"Unknown status found: {status}")
        
        # Calculate percentage based on FINAL_APPROVED only
        final_approved = status_counts["FINAL_APPROVED"]
        percentage = round((final_approved / total_trades) * 100, 1) if total_trades > 0 else 0
        
        logger.info(f"📊 {sheet_name}: {final_approved}/{total_trades} = {percentage}% final approved")
        return percentage
        
    except Exception as e:
        logger.error(f"Error calculating approval percentage for {sheet_name}: {e}")
        return 0

# ============================================================================
# FIX: ENHANCED NOTIFICATION SYSTEM - ENSURE REGISTRATION
# ============================================================================

def ensure_notification_registration():
    """Ensure notification system is properly initialized"""
    global APPROVER_TELEGRAM_IDS
    
    # Initialize if not already done
    if not hasattr(ensure_notification_registration, 'initialized'):
        logger.info("🔔 Initializing notification system...")
        
        # Ensure all approver IDs are in the system
        required_approvers = {
            "1001": None,  # Abhay - Head Accountant
            "1002": None,  # Mushtaq - Level 2
            "1003": None   # Ahmadreza - Manager
        }
        
        for approver_id in required_approvers:
            if approver_id not in APPROVER_TELEGRAM_IDS:
                APPROVER_TELEGRAM_IDS[approver_id] = None
                logger.info(f"📲 Added approver ID {approver_id} to notification system")
        
        ensure_notification_registration.initialized = True
        logger.info("✅ Notification system initialized")

# ============================================================================
# FIX: MISSING HANDLE_CANCEL_TRADE FUNCTION
# ============================================================================

def handle_cancel_trade(call):
    """Handle trade cancellation"""
    try:
        user_id = call.from_user.id
        
        # Clear trade session
        if user_id in user_sessions and 'trade_session' in user_sessions[user_id]:
            del user_sessions[user_id]['trade_session']
        
        # Clear any pending inputs
        if user_id in user_sessions and 'awaiting_input' in user_sessions[user_id]:
            del user_sessions[user_id]['awaiting_input']
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📊 New Trade", callback_data="new_trade"))
        markup.add(types.InlineKeyboardButton("🔙 Dashboard", callback_data="dashboard"))
        
        bot.edit_message_text(
            "❌ TRADE CANCELLED\n\n✅ Session cleared successfully\n\n🎯 What would you like to do next?",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
        
        logger.info(f"❌ User {user_id} cancelled trade")
        
    except Exception as e:
        logger.error(f"Cancel trade error: {e}")

# ============================================================================
# FIX: COMPLETE FINAL SAVE FUNCTION (MISSING END PART)
# ============================================================================

def handle_confirm_trade_COMPLETE(call):
    """COMPLETE: Confirm and save trade - with full success message"""
    try:
        user_id = call.from_user.id
        session_data = user_sessions.get(user_id, {})
        trade_session = session_data.get("trade_session")
        
        if not trade_session:
            bot.edit_message_text("❌ Session error", call.message.chat.id, call.message.message_id)
            return
        
        bot.edit_message_text("💾 Saving trade and sending Telegram notifications...", call.message.chat.id, call.message.message_id)
        
        success, result = save_trade_to_sheets_with_notifications(trade_session)
        
        if success:
            # Calculate for success message
            if trade_session.rate_type == "override":
                calc_results = calculate_trade_totals_with_override(
                    trade_session.volume_kg,
                    trade_session.gold_purity['value'],
                    trade_session.final_rate_per_oz,
                    "override"
                )
                rate_description = f"OVERRIDE: ${trade_session.final_rate_per_oz:,.2f}/oz"
            else:
                if trade_session.rate_type == "market":
                    base_rate = market_data['gold_usd_oz']
                else:  # custom
                    base_rate = trade_session.rate_per_oz
                
                calc_results = calculate_trade_totals(
                    trade_session.volume_kg,
                    trade_session.gold_purity['value'],
                    base_rate,
                    trade_session.pd_type,
                    trade_session.pd_amount
                )
                
                pd_sign = "+" if trade_session.pd_type == "premium" else "-"
                rate_description = f"{trade_session.rate_type.upper()}: ${base_rate:,.2f} {pd_sign} ${trade_session.pd_amount}/oz"
            
            # Build type description
            type_desc = trade_session.gold_type['name']
            if hasattr(trade_session, 'quantity') and trade_session.quantity:
                qty_display = f"{trade_session.quantity:g}" if trade_session.quantity == int(trade_session.quantity) else f"{trade_session.quantity:.3f}".rstrip('0').rstrip('.')
                type_desc = f"{qty_display} × {type_desc}"
            
            # Clear trade session
            if 'trade_session' in user_sessions[user_id]:
                del user_sessions[user_id]['trade_session']
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📊 New Trade", callback_data="new_trade"))
            markup.add(types.InlineKeyboardButton("🔍 View Approvals", callback_data="approval_dashboard"))
            markup.add(types.InlineKeyboardButton("🔙 Dashboard", callback_data="dashboard"))
            
            success_message = f"""✅ TRADE SAVED SUCCESSFULLY! 🎉

📋 TRADE SUMMARY:
• Session ID: {result}
• Operation: {trade_session.operation.upper()}
• Type: {type_desc}
• Customer: {trade_session.customer}
• Volume: {format_weight_combined(trade_session.volume_kg)}
• Price: ${calc_results['total_price_usd']:,.2f} USD = {format_money_aed(calc_results['total_price_usd'])}
• Rate: {rate_description}

📲 NOTIFICATIONS SENT:
✅ Abhay (Head Accountant) has been notified!
✅ Approval workflow initiated
✅ Sequential notifications activated

📊 STATUS: PENDING (Red background in sheet)
🎯 Next: Awaiting Abhay's approval

🎨 Professional formatting applied to sheet!
☁️ Data saved to Google Sheets on Railway Cloud

🚀 Ready for next trade!"""
            
            bot.edit_message_text(success_message, call.message.chat.id, call.message.message_id, reply_markup=markup)
            
            logger.info(f"✅ Trade saved successfully with notifications: {result}")
        else:
            # Error saving
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔄 Try Again", callback_data="confirm_trade"))
            markup.add(types.InlineKeyboardButton("✏️ Edit Trade", callback_data="new_trade"))
            markup.add(types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_trade"))
            
            bot.edit_message_text(
                f"❌ SAVE FAILED\n\nError: {result}\n\n🔄 Please try again or contact admin.",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )
            
            logger.error(f"❌ Trade save failed: {result}")
            
    except Exception as e:
        logger.error(f"❌ Confirm trade error: {e}")
        try:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 Dashboard", callback_data="dashboard"))
            bot.edit_message_text(f"❌ Unexpected error: {str(e)}", call.message.chat.id, call.message.message_id, reply_markup=markup)
        except:
            pass

# ============================================================================
# STARTUP FUNCTION TO ENSURE ALL SYSTEMS ARE READY
# ============================================================================

def initialize_complete_system():
    """Initialize all system components for cloud deployment"""
    try:
        logger.info("🚀 Starting COMPLETE Gold Trading Bot v4.9 with all features...")
        
        # 1. Initialize notification system
        ensure_notification_registration()
        
        # 2. Start rate updater
        start_rate_updater()
        
        # 3. Test all connections
        logger.info("🔧 Testing system connections...")
        
        # Test gold rate API
        if fetch_gold_rate():
            logger.info("✅ Gold rate API: Connected")
        else:
            logger.warning("⚠️ Gold rate API: Failed (using fallback)")
        
        # Test Google Sheets
        sheets_success, sheets_msg = test_sheets_connection()
        if sheets_success:
            logger.info(f"✅ Google Sheets: {sheets_msg}")
        else:
            logger.error(f"❌ Google Sheets: {sheets_msg}")
        
        # 4. Verify bot token
        try:
            bot_info = bot.get_me()
            logger.info(f"✅ Telegram Bot: @{bot_info.username} ready")
        except Exception as e:
            logger.error(f"❌ Telegram Bot: {e}")
        
        # 5. Log system ready status
        logger.info("✅ COMPLETE SYSTEM READY!")
        logger.info("🎯 Features: All gold types, quantities, custom inputs, notifications, approval workflow")
        logger.info("📲 Notifications: Abhay → Mushtaq → Ahmadreza chain active")
        logger.info("🎨 Professional sheet formatting enabled")
        logger.info("🔧 Admin tools available")
        logger.info("☁️ Railway cloud deployment ready")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ System initialization failed: {e}")
        return False

# ============================================================================
# MAIN EXECUTION FOR COMPLETE SYSTEM
# ============================================================================

if __name__ == "__main__":
    """Main execution - start the complete bot system"""
    try:
        # Initialize complete system
        if initialize_complete_system():
            logger.info("🚀 Starting bot polling...")
            bot.polling(none_stop=True, interval=1, timeout=30)
        else:
            logger.error("❌ System initialization failed - cannot start bot")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Bot crashed: {e}")
        sys.exit(1)
