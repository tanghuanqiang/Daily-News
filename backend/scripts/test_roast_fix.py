#!/usr/bin/env python3
"""
测试吐槽模式修复效果
验证 prompt 优化和后处理逻辑是否有效防止泄露
"""

import sys
import os

# 添加backend目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from summarizer import get_summarizer

def test_roast_generation():
    """测试吐槽生成，确保没有 prompt 泄露"""
    print("=" * 60)
    print("测试吐槽模式修复效果")
    print("=" * 60)
    
    # 测试数据
    test_cases = [
        {
            "title": "科技巨头发布新款AI眼镜",
            "content": "某科技巨头今日发布了新款AI眼镜，集成了最新的人工智能技术，可以实时翻译、识别物体并提供信息。售价2999美元，预计下月上市。",
            "topic": "科技"
        },
        {
            "title": "股市大涨创新高",
            "content": "今日股市全线上涨，主要指数均创出历史新高。分析师认为，经济数据向好和企业盈利增长是主要推动力。",
            "topic": "财经"
        }
    ]
    
    summarizer = get_summarizer()
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n【测试用例 {i}】")
        print(f"标题: {case['title']}")
        print(f"内容: {case['content'][:80]}...")
        
        try:
            # 生成吐槽
            roast = summarizer.generate_summary(
                title=case['title'],
                content=case['content'],
                roast_mode=True,
                topic=case['topic']
            )
            
            print(f"\n生成结果: {roast}")
            print(f"长度: {len(roast)} 字")
            
            # 检查是否有 prompt 泄露
            leak_indicators = [
                '分析请求', '角色', '任务', '要求',
                '**', '1.', '2.', '3.',
                '你是一个', '新闻标题', '新闻内容'
            ]
            
            found_leaks = []
            for indicator in leak_indicators:
                if indicator in roast:
                    found_leaks.append(indicator)
            
            if found_leaks:
                print(f"❌ 发现泄露: {', '.join(found_leaks)}")
            else:
                print("✅ 未发现 prompt 泄露")
            
        except Exception as e:
            print(f"❌ 生成失败: {e}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_roast_generation()
