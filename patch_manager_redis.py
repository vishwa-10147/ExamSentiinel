import sys

with open(r'backend\app\websocket\manager.py', 'r') as f:
    text = f.read()

def safe_publish(channel, message_str):
    return f'''        try:
            await redis_client.publish(self.channel_name, json.dumps(message))
        except Exception as e:
            logger.debug(f"Redis publish failed: {{e}}")
            # Fallback to local broadcast if Redis is unavailable (useful for tests)
            await self._broadcast_to_all_tiers_local(session_id, exam_id, message)'''

text = text.replace('await redis_client.publish(self.channel_name, json.dumps(message))', safe_publish(1,1))

with open(r'backend\app\websocket\manager.py', 'w') as f:
    f.write(text)
