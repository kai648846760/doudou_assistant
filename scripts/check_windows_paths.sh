#!/usr/bin/env bash
# 检查 Windows 非法路径的脚本
# 此脚本扫描仓库中所有文件和目录名，找出在 Windows 上不合法的路径

set -eo pipefail

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔍 开始检查 Windows 非法路径..."
echo ""

# Windows 非法字符: < > : " / \ | ? *
# 保留名称: CON, PRN, AUX, NUL, COM1-9, LPT1-9
INVALID_CHARS='[<>:"|?*]'
RESERVED_NAMES="^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\.|$)"

violations=()
violation_count=0

# 获取 git 仓库根目录
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo ".")
cd "$REPO_ROOT"

# 遍历所有被 git 追踪的文件（排除 .git 目录）
while IFS= read -r -d '' file; do
    # 提取文件名（不含路径）
    filename=$(basename "$file")
    dirname=$(dirname "$file")
    
    # 检查非法字符
    if echo "$filename" | grep -qE "$INVALID_CHARS"; then
        violations+=("❌ 非法字符: $file")
        violation_count=$((violation_count + 1))
        continue
    fi
    
    # 检查反斜杠（在某些系统上可能被解析为路径分隔符）
    if [[ "$filename" == *'\\'* ]]; then
        violations+=("❌ 包含反斜杠: $file")
        violation_count=$((violation_count + 1))
        continue
    fi
    
    # 检查尾随空格或点
    if [[ "$filename" =~ [\ \.]+$ ]]; then
        violations+=("❌ 尾随空格或点: $file")
        violation_count=$((violation_count + 1))
        continue
    fi
    
    # 检查保留名称（不区分大小写）
    filename_upper=$(echo "$filename" | tr '[:lower:]' '[:upper:]')
    # 检查完整文件名或去除扩展名后的名称
    basename_no_ext="${filename_upper%.*}"
    if echo "$filename_upper" | grep -qE "$RESERVED_NAMES" || echo "$basename_no_ext" | grep -qE "$RESERVED_NAMES"; then
        violations+=("❌ Windows 保留名称: $file")
        violation_count=$((violation_count + 1))
        continue
    fi
    
    # 检查路径中的所有组件
    if [[ "$dirname" != "." ]]; then
        IFS='/' read -ra PATH_PARTS <<< "$dirname"
        for part in "${PATH_PARTS[@]}"; do
            if [[ -n "$part" && "$part" != "." ]]; then
                # 检查目录名非法字符
                if echo "$part" | grep -qE "$INVALID_CHARS"; then
                    violations+=("❌ 目录名含非法字符: $file")
                    violation_count=$((violation_count + 1))
                    break
                fi
                
                # 检查目录名尾随空格或点
                if [[ "$part" =~ [\ \.]+$ ]]; then
                    violations+=("❌ 目录名尾随空格或点: $file")
                    violation_count=$((violation_count + 1))
                    break
                fi
                
                # 检查目录保留名称
                part_upper=$(echo "$part" | tr '[:lower:]' '[:upper:]')
                if echo "$part_upper" | grep -qE "$RESERVED_NAMES"; then
                    violations+=("❌ 目录是 Windows 保留名称: $file")
                    violation_count=$((violation_count + 1))
                    break
                fi
            fi
        done
    fi
done < <(git ls-files -z 2>/dev/null)

# 输出结果
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ $violation_count -eq 0 ]; then
    echo -e "${GREEN}✅ 太好了！未发现 Windows 非法路径。${NC}"
    echo ""
    echo "所有文件名都符合 Windows 文件系统要求。"
    exit 0
else
    echo -e "${RED}❌ 发现 $violation_count 个 Windows 非法路径：${NC}"
    echo ""
    for violation in "${violations[@]}"; do
        echo -e "$violation"
    done
    echo ""
    echo -e "${YELLOW}📋 Windows 文件名限制说明：${NC}"
    echo "• 不能包含字符: < > : \" / \\ | ? *"
    echo "• 不能以空格或点结尾"
    echo "• 不能使用保留名称: CON, PRN, AUX, NUL, COM1-9, LPT1-9"
    echo ""
    echo "请重命名或删除上述文件后再提交代码。"
    exit 1
fi
