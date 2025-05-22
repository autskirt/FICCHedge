import streamlit as st
import pandas as pd
import time
import os
import tempfile
from datetime import datetime
import io
import sys
import traceback
import shutil

# 设置页面配置
st.set_page_config(
    page_title="对冲计算管理系统",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f2937;
        text-align: center;
        margin-bottom: 2rem;
        background: linear-gradient(90deg, #3b82f6, #10b981);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .upload-section {
        background-color: #f8fafc;
        padding: 1.5rem;
        border-radius: 10px;
        border: 2px dashed #cbd5e1;
        margin: 1rem 0;
    }
    .result-card {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# 🔧 文件名映射 - 解决中文文件名问题的核心
FILE_MAPPING = {
    'receipt_flow': '浮动收益凭证流水.xlsx',
    'variety_mapping': '品种映射表.xlsx', 
    'index_hedge_weight': '指数对冲权重.xlsx',
    'index_scale': '指数规模.xlsx',
    'asset_list': 'asset_list.xlsx'
}

def save_uploaded_file(uploaded_file, target_filename):
    """直接保存文件到指定的中文文件名"""
    try:
        current_dir = os.getcwd()
        file_path = os.path.join(current_dir, target_filename)
        
        # 使用二进制模式写入，避免编码问题
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # 验证文件
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            return file_path
        else:
            return None
    except Exception as e:
        st.error(f"保存文件失败: {str(e)}")
        return None

def main():
    # 页面标题
    st.markdown('<h1 class="main-header">📊 对冲计算管理系统</h1>', unsafe_allow_html=True)
    
    # 显示当前工作目录
    current_dir = os.getcwd()
    st.info(f"📁 当前工作目录: {current_dir}")
    
    # 侧边栏
    with st.sidebar:
        st.markdown("### 🔧 系统操作")
        page = st.selectbox("选择功能", ["数据上传", "计算结果", "系统状态"])
        
        st.markdown("---")
        st.markdown("### 📝 使用说明")
        st.info("1. 上传5个必需的数据文件\n2. 文件会自动保存为正确的中文文件名\n3. 执行计算操作")
        
        st.markdown("---")
        st.markdown("### 📋 需要的文件")
        for key, filename in FILE_MAPPING.items():
            st.write(f"• {filename}")
    
    # 初始化session state
    if 'files_status' not in st.session_state:
        st.session_state.files_status = {}
    if 'calculation_results' not in st.session_state:
        st.session_state.calculation_results = {}

    if page == "数据上传":
        show_upload_page()
    elif page == "计算结果":
        show_results_page()
    elif page == "系统状态":
        show_status_page()

def show_upload_page():
    st.markdown("## 📁 数据文件上传")
    
    file_labels = {
        'receipt_flow': '浮动收益凭证流水',
        'variety_mapping': '品种映射表', 
        'index_hedge_weight': '指数对冲权重',
        'index_scale': '指数规模',
        'asset_list': 'Asset List'
    }
    
    # 创建上传区域
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 数据文件")
        
        # 浮动收益凭证流水
        receipt_file = st.file_uploader(
            "上传: 浮动收益凭证流水", 
            type=['xlsx', 'xls'],
            key='receipt_upload',
            help="请上传Excel格式的浮动收益凭证流水文件"
        )
        if receipt_file:
            target_file = FILE_MAPPING['receipt_flow']
            if save_uploaded_file(receipt_file, target_file):
                st.success(f"✅ 已保存为: {target_file}")
                st.session_state.files_status['receipt_flow'] = True
        
        # 品种映射表
        variety_file = st.file_uploader(
            "上传: 品种映射表", 
            type=['xlsx', 'xls'],
            key='variety_upload',
            help="请上传Excel格式的品种映射表"
        )
        if variety_file:
            target_file = FILE_MAPPING['variety_mapping']
            if save_uploaded_file(variety_file, target_file):
                st.success(f"✅ 已保存为: {target_file}")
                st.session_state.files_status['variety_mapping'] = True
        
        # 指数对冲权重
        weight_file = st.file_uploader(
            "上传: 指数对冲权重", 
            type=['xlsx', 'xls'],
            key='weight_upload',
            help="请上传Excel格式的指数对冲权重文件"
        )
        if weight_file:
            target_file = FILE_MAPPING['index_hedge_weight']
            if save_uploaded_file(weight_file, target_file):
                st.success(f"✅ 已保存为: {target_file}")
                st.session_state.files_status['index_hedge_weight'] = True
    
    with col2:
        st.markdown("### 📈 配置文件")
        
        # 指数规模
        scale_file = st.file_uploader(
            "上传: 指数规模", 
            type=['xlsx', 'xls'],
            key='scale_upload',
            help="请上传Excel格式的指数规模文件"
        )
        if scale_file:
            target_file = FILE_MAPPING['index_scale']
            if save_uploaded_file(scale_file, target_file):
                st.success(f"✅ 已保存为: {target_file}")
                st.session_state.files_status['index_scale'] = True
        
        # Asset List
        asset_file = st.file_uploader(
            "上传: Asset List", 
            type=['xlsx', 'xls'],
            key='asset_upload',
            help="请上传Excel格式的资产列表文件"
        )
        if asset_file:
            target_file = FILE_MAPPING['asset_list']
            if save_uploaded_file(asset_file, target_file):
                st.success(f"✅ 已保存为: {target_file}")
                st.session_state.files_status['asset_list'] = True
    
    # 显示文件状态
    st.markdown("---")
    st.markdown("### 📋 文件状态检查")
    
    status_cols = st.columns(5)
    for i, (key, label) in enumerate(file_labels.items()):
        with status_cols[i]:
            target_file = FILE_MAPPING[key]
            if os.path.exists(target_file):
                file_size = os.path.getsize(target_file)
                st.success(f"✅ {label}")
                st.caption(f"📏 {file_size/1024:.1f} KB")
                st.session_state.files_status[key] = True
            else:
                st.error(f"❌ {label}")
                st.session_state.files_status[key] = False
    
    # 计算按钮
    all_files_ready = all(st.session_state.files_status.get(key, False) for key in FILE_MAPPING.keys())
    
    st.markdown("---")
    st.markdown("### 🚀 执行计算")
    
    calc_col1, calc_col2 = st.columns(2)
    
    with calc_col1:
        if st.button("🔵 指数对冲计算", disabled=not all_files_ready, use_container_width=True):
            execute_index_hedge_calculation()
    
    with calc_col2:
        if st.button("🟢 非指数对冲计算", disabled=not all_files_ready, use_container_width=True):
            execute_non_index_hedge_calculation()
    
    if not all_files_ready:
        missing_files = [FILE_MAPPING[key] for key, status in st.session_state.files_status.items() if not status]
        st.warning(f"⚠️ 请先上传缺少的文件: {', '.join(missing_files)}")

def execute_index_hedge_calculation():
    """执行指数对冲计算"""
    st.markdown("### 🔄 正在执行指数对冲计算...")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # 检查模块
        status_text.text("🔍 检查模块...")
        progress_bar.progress(10)
        
        try:
            import index_hedge_new
            status_text.text("✅ 模块导入成功")
            progress_bar.progress(20)
        except ImportError as e:
            st.error(f"❌ 无法导入index_hedge_new模块: {str(e)}")
            return
        
        # 执行计算
        status_text.text("🔄 正在计算指数规模...")
        progress_bar.progress(40)
        
        amt = index_hedge_new.calculate_index_amounts()
        progress_bar.progress(70)
        
        status_text.text("🔄 正在计算期货仓位...")
        total_position = index_hedge_new.calculate_positions(amt)
        progress_bar.progress(90)
        
        # 格式化结果
        result_data = []
        for contract in total_position.columns:
            position_value = total_position.loc[total_position.index[-1], contract]
            result_data.append({
                'contract': contract,
                'position': float(position_value),
                'amount': float(position_value * 100000)
            })
        
        result = {
            'timestamp': datetime.now(),
            'total_position': pd.DataFrame(result_data),
            'raw_result': total_position
        }
        
        progress_bar.progress(100)
        status_text.text("✅ 计算完成！")
        
        st.session_state.calculation_results['index_hedge'] = result
        st.success("✅ 指数对冲计算完成！")
        st.balloons()
        
    except Exception as e:
        st.error(f"❌ 计算失败: {str(e)}")
        st.code(traceback.format_exc())

def execute_non_index_hedge_calculation():
    """执行非指数对冲计算"""
    st.markdown("### 🔄 正在执行非指数对冲计算...")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.text("🔍 检查模块...")
        progress_bar.progress(10)
        
        try:
            import nonindex_hedge
            status_text.text("✅ 模块导入成功")
            progress_bar.progress(20)
        except ImportError as e:
            st.error(f"❌ 无法导入nonindex_hedge模块: {str(e)}")
            return
        
        status_text.text("🔄 正在生成要素表数据...")
        progress_bar.progress(30)
        
        snowball_data, other_data = nonindex_hedge.create_element_summary_data()
        progress_bar.progress(50)
        
        status_text.text("🔄 正在处理小雪球产品...")
        snowball_assets = {}
        if snowball_data:
            snowball_assets = nonindex_hedge.run_estimation_on_data(snowball_data, "小雪球")
        progress_bar.progress(70)
        
        status_text.text("🔄 正在处理非小雪球产品...")
        other_assets = {}
        if other_data:
            other_assets = nonindex_hedge.run_estimation_on_data(other_data, "非小雪球")
        progress_bar.progress(85)
        
        status_text.text("🔄 正在汇总结果...")
        all_assets = {}
        
        # 汇总小雪球
        if snowball_assets:
            for product_name, product_data in snowball_assets.items():
                for k, v in product_data.items():
                    all_assets[k] = all_assets.get(k, 0) + v
        
        # 加上非小雪球
        for k, v in other_assets.items():
            all_assets[k] = all_assets.get(k, 0) + v
        
        # 简化的主力合约映射
        main_contracts = {}
        for asset, amount in all_assets.items():
            contract_name = asset.lower().replace('.shf', '2506').replace('.cfe', '2506')
            main_contracts[contract_name] = amount
        
        result = {
            'timestamp': datetime.now(),
            'snowball_products': snowball_assets,
            'non_snowball_summary': other_assets,
            'total_summary': all_assets,
            'main_contracts': main_contracts
        }
        
        progress_bar.progress(100)
        status_text.text("✅ 计算完成！")
        
        st.session_state.calculation_results['non_index_hedge'] = result
        st.success("✅ 非指数对冲计算完成！")
        st.balloons()
        
    except Exception as e:
        st.error(f"❌ 计算失败: {str(e)}")
        st.code(traceback.format_exc())

def show_results_page():
    st.markdown("## 📊 计算结果")
    
    if not st.session_state.calculation_results:
        st.info("🔍 暂无计算结果，请先执行计算操作。")
        return
    
    available_results = []
    if 'index_hedge' in st.session_state.calculation_results:
        available_results.append("指数对冲结果")
    if 'non_index_hedge' in st.session_state.calculation_results:
        available_results.append("非指数对冲结果")
    
    if not available_results:
        st.warning("⚠️ 暂无可用结果")
        return
    
    result_type = st.selectbox("选择结果类型", available_results)
    
    if result_type == "指数对冲结果":
        show_index_hedge_results()
    elif result_type == "非指数对冲结果":
        show_non_index_hedge_results()

def show_index_hedge_results():
    """显示指数对冲结果"""
    result = st.session_state.calculation_results['index_hedge']
    
    st.markdown("### 🔵 指数对冲计算结果")
    st.info(f"📅 计算时间: {result['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
    
    df = result['total_position']
    df_display = df.copy()
    df_display['amount'] = df_display['amount'].apply(lambda x: f"¥{x:,.2f}")
    df_display['position'] = df_display['position'].apply(lambda x: f"{x:.2f}")
    
    st.dataframe(df_display, use_container_width=True)
    
    if 'raw_result' in result:
        with st.expander("🔍 查看原始计算结果"):
            st.dataframe(result['raw_result'], use_container_width=True)
    
    csv = df.to_csv(index=False)
    st.download_button(
        label="📥 下载结果 (CSV)",
        data=csv,
        file_name=f"index_hedge_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )

def show_non_index_hedge_results():
    """显示非指数对冲结果"""
    result = st.session_state.calculation_results['non_index_hedge']
    
    st.markdown("### 🟢 非指数对冲计算结果")
    st.info(f"📅 计算时间: {result['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
    
    view_mode = st.radio("选择查看模式", ["汇总视图", "详细视图"], horizontal=True)
    
    if view_mode == "详细视图":
        if result['snowball_products']:
            st.markdown("#### ❄️ 小雪球产品明细")
            for product_name, assets in result['snowball_products'].items():
                with st.expander(f"📋 {product_name}"):
                    if assets:
                        df = pd.DataFrame(list(assets.items()), columns=['资产', 'Amount'])
                        df['Amount'] = df['Amount'].apply(lambda x: f"{x:.2f}")
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("该产品暂无数据")
        
        if result['non_snowball_summary']:
            st.markdown("#### 📊 非小雪球产品汇总")
            df_non_snowball = pd.DataFrame(list(result['non_snowball_summary'].items()), 
                                          columns=['资产', 'Amount'])
            df_non_snowball['Amount'] = df_non_snowball['Amount'].apply(lambda x: f"{x:.2f}")
            st.dataframe(df_non_snowball, use_container_width=True)
    
    if result['total_summary']:
        st.markdown("#### 📈 标的资产总汇总")
        df_total = pd.DataFrame(list(result['total_summary'].items()), columns=['资产', 'Amount'])
        df_total['Amount'] = df_total['Amount'].apply(lambda x: f"{x:.2f}")
        st.dataframe(df_total, use_container_width=True)
    
    if result['main_contracts']:
        st.markdown("#### 🎯 主力合约汇总")
        df_main = pd.DataFrame(list(result['main_contracts'].items()), columns=['主力合约', 'Amount'])
        df_main['Amount'] = df_main['Amount'].apply(lambda x: f"{x:.2f}")
        st.dataframe(df_main, use_container_width=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if result['total_summary']:
            csv_total = df_total.to_csv(index=False)
            st.download_button(
                label="📥 下载总汇总 (CSV)",
                data=csv_total,
                file_name=f"non_index_total_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    with col2:
        if result['main_contracts']:
            csv_main = df_main.to_csv(index=False)
            st.download_button(
                label="📥 下载主力合约 (CSV)",
                data=csv_main,
                file_name=f"main_contracts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

def show_status_page():
    st.markdown("## ⚙️ 系统状态")
    
    current_dir = os.getcwd()
    st.markdown("### 📁 文件状态")
    
    for key, filename in FILE_MAPPING.items():
        file_path = os.path.join(current_dir, filename)
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            st.success(f"✅ {filename}: {file_size/1024:.1f} KB")
        else:
            st.error(f"❌ {filename}: 文件不存在")
    
    st.markdown("### 🔄 计算状态")
    if st.session_state.calculation_results:
        for calc_type, result in st.session_state.calculation_results.items():
            st.success(f"✅ {calc_type}: 已完成 ({result['timestamp'].strftime('%H:%M:%S')})")
    else:
        st.info("📊 暂无计算结果")
    
    st.markdown("### 🔧 模块状态检查")
    modules_to_check = ['index_hedge_new', 'nonindex_hedge', 'asset', 'futures']
    
    for module_name in modules_to_check:
        try:
            __import__(module_name)
            st.success(f"✅ {module_name}: 可用")
        except ImportError:
            st.error(f"❌ {module_name}: 未找到")
    
    st.markdown("### 🗑️ 系统清理")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗂️ 删除所有上传文件"):
            for filename in FILE_MAPPING.values():
                if os.path.exists(filename):
                    os.remove(filename)
            st.session_state.files_status = {}
            st.success("✅ 已删除所有文件")
            st.rerun()
    
    with col2:
        if st.button("📊 清除计算结果"):
            st.session_state.calculation_results = {}
            st.success("✅ 已清除计算结果")
            st.rerun()

if __name__ == "__main__":
    main()