#!/bin/bash
# f-string HTML 语法检查脚本
# 问题: f"<b style='color:{COLOR['key']}'>text</b>" 中 '>' 紧跟 {expr}
# 解决: 用 + 拼接，或在 } 后加空格
#
# 用法: bash scripts/check_fstring_html.sh
echo "=== 检查 f-string + HTML 语法 ==="
problem_count=0

while IFS= read -r file; do
    line_num=0
    while IFS= read -r line; do
        line_num=$((line_num+1))
        if [[ "$line" =~ f[\"'] ]]; then
            # 检测 } 后面紧跟 HTML 可见文本（如 >text 或 >字）
            # 用 printf 避免 heredoc 中的 > 解析问题
            if printf '%s' "$line" | grep -qE '\}>[a-zA-Z\u4e00-\u9fff]'; then
                echo "WARN $file:$line_num"
                echo "   $(printf '%s' "$line" | cut -c1-150)"
                problem_count=$((problem_count+1))
            fi
        fi
    done < "$file"
done < <(find . -name "*.py" -not -path "./.venv/*" -not -path "*/site-packages/*" -not -path "./scripts/*")

if [ $problem_count -eq 0 ]; then
    echo "OK 未发现 f-string HTML 语法问题"
else
    echo "=== 发现 $problem_count 个可疑行 ==="
fi