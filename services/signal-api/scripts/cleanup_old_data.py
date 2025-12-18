#!/usr/bin/env python3
"""
数据清理工具 - 删除过期数据，释放存储空间

默认保留最近90天数据
"""

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlite3
from datetime import datetime, timedelta
import argparse

def cleanup_checkpoints(keep_days, dry_run=False):
    """清理checkpoint数据库"""
    print(f"\n📊 Checkpoint 数据库清理 (保留{keep_days}天)")
    print("=" * 60)
    
    db_path = 'quant_data/checkpoints.db'
    if not os.path.exists(db_path):
        print("❌ 数据库不存在")
        return
    
    cutoff = (datetime.now() - timedelta(days=keep_days)).strftime("%Y-%m-%d")
    
    conn = sqlite3.connect(db_path)
    
    # 查询要删除的记录数
    cursor = conn.execute(
        "SELECT count(*) FROM sync_checkpoints WHERE trade_date < ?",
        (cutoff,)
    )
    to_delete = cursor.fetchone()[0]
    
    print(f"找到 {to_delete:,} 条过期记录 (早于 {cutoff})")
    
    if to_delete == 0:
        print("✅ 无需清理")
        conn.close()
        return
    
    if dry_run:
        print("🔍 预览模式 - 未实际删除")
    else:
        conn.execute("DELETE FROM sync_checkpoints WHERE trade_date < ?", (cutoff,))
        conn.commit()
        print(f"✅ 已删除 {to_delete:,} 条记录")
        
        # 压缩数据库
        conn.execute("VACUUM")
        print("✅ 已压缩数据库")
    
    conn.close()

def cleanup_parquet_files(keep_days, dry_run=False):
    """清理DuckDB Parquet文件"""
    print(f"\n💾 Parquet 文件清理 (保留{keep_days}天)")
    print("=" * 60)
    
    data_dir = Path('quant_data')
    if not data_dir.exists():
        print("❌ 数据目录不存在")
        return
    
    cutoff_date = datetime.now() - timedelta(days=keep_days)
    
    old_files = []
    total_size = 0
    
    for file_path in data_dir.glob('*.parquet'):
        # 根据文件修改时间判断
        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        if mtime < cutoff_date:
            size = file_path.stat().st_size
            old_files.append((file_path, size))
            total_size += size
    
    if not old_files:
        print("✅ 无过期文件")
        return
    
    print(f"找到 {len(old_files)} 个过期文件，共 {total_size/1024/1024:.2f} MB")
    
    if dry_run:
        print("🔍 预览模式 - 未实际删除")
        for file_path, size in old_files[:10]:  # 只显示前10个
            print(f"  - {file_path.name} ({size/1024:.1f} KB)")
    else:
        for file_path, _ in old_files:
            file_path.unlink()
        print(f"✅ 已删除 {len(old_files)} 个文件，释放 {total_size/1024/1024:.2f} MB")

def get_storage_stats():
    """显示存储统计"""
    print(f"\n📈 存储空间统计")
    print("=" * 60)
    
    data_dir = Path('quant_data')
    if not data_dir.exists():
        return
    
    total_size = 0
    file_count = 0
    
    for file_path in data_dir.rglob('*'):
        if file_path.is_file():
            total_size += file_path.stat().st_size
            file_count += 1
    
    print(f"数据目录: {data_dir.absolute()}")
    print(f"文件数量: {file_count:,}")
    print(f"总大小: {total_size/1024/1024:.2f} MB")

def main():
    parser = argparse.ArgumentParser(description='数据清理工具')
    parser.add_argument('--keep-days', type=int, default=90, help='保留天数 (默认90)')
    parser.add_argument('--dry-run', action='store_true', help='预览模式，不实际删除')
    parser.add_argument('--skip-parquet', action='store_true', help='跳过Parquet清理')
    
    args = parser.parse_args()
    
    print("\n" + "🧹 东风破 - 数据清理工具".center(60, "="))
    print(f"保留天数: {args.keep_days}")
    print(f"模式: {'🔍 预览' if args.dry_run else '⚠️  执行'}")
    
    get_storage_stats()
    cleanup_checkpoints(args.keep_days, args.dry_run)
    
    if not args.skip_parquet:
        cleanup_parquet_files(args.keep_days, args.dry_run)
    
    print("\n" + "=" * 60)
    if args.dry_run:
        print("💡 提示: 使用不带 --dry-run 参数执行实际清理")
    else:
        print("✅ 清理完成!")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    os.chdir(Path(__file__).parent.parent)
    main()
