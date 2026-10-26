import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import google.generativeai as genai
import json
import os
import time

class GeminiControlNode(Node):
    def __init__(self):
        super().__init__('gemini_control_node')
        self.publisher_ = self.create_publisher(Twist, '/cmd_vel', 10)
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        
        system_instruction = """
        あなたはロボットの制御AIです。ユーザーの自然言語の指示を解釈し、以下のJSONフォーマットのみを出力してください。
        {"linear_x": 前進/後退速度(float), "angular_z": 回転速度(float), "duration": 継続時間(float)}
        
        【動作原則】
        ・座標系：前進はプラス、後退はマイナス。回転は左回りをプラス（例: 1.0）、右回りをマイナス（例: -1.0）とする。
        ・最終意図の抽出：言い直しや取り消しが含まれる場合、最終的な意図のみを抽出し、破棄された指示は無視する。
        ・対話の継続：過去の指示の文脈を引き継いで新しいJSONを生成する。
        ・感覚的表現：少し=0.2、速く=0.8など適宜スケーリングする。最大速度は1.0とする。
        ・出力は必ずJSONのみとし、余計なテキストを含めないこと。
        """
        self.model = genai.GenerativeModel(model_name='models/gemini-3.8-flash', system_instruction=system_instruction)
        self.chat_session = self.model.start_chat(history=[])
        self.get_logger().info('Gemini対話型AIノードが起動しました')
        self.run_interactive_loop()

    def run_interactive_loop(self):
        while rclpy.ok():
            user_input = input("ロボットへの指示を入力してください（例: '3秒前進して', '終了'）: ")
            if user_input == '終了':
                break
            self.get_logger().info('Geminiが思考中...')
            try:
                response = self.chat_session.send_message(user_input)
                text = response.text.strip()
                if text.startswith("```json"): text = text[7:-3].strip()
                elif text.startswith("```"): text = text[3:-3].strip()
                
                data = json.loads(text)
                linear_x = float(data.get('linear_x', 0.0))
                angular_z = float(data.get('angular_z', 0.0))
                duration = float(data.get('duration', 0.0))
                
                self.get_logger().info(f"解釈結果: 前進={linear_x}, 回転={angular_z}, 継続時間={duration}秒")
                self.publish_command(linear_x, angular_z, duration)
            except Exception as e:
                self.get_logger().error(f"エラー発生: {e}")

    def publish_command(self, linear_x, angular_z, duration):
        twist = Twist()
        twist.linear.x = linear_x
        twist.angular.z = angular_z
        self.publisher_.publish(twist)
        time.sleep(duration)
        twist.linear.x = 0.0
        twist.angular.z = 0.0
        self.publisher_.publish(twist)
        self.get_logger().info('動作完了。次の指示をお待ちしています。')

def main(args=None):
    rclpy.init(args=args)
    node = GeminiControlNode()
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()