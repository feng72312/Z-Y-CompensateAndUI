# Change: 添加图像平面标准差平均值显示

## Why
完整流程中目前只显示RMS误差，但用户需要了解每张深度图平面内的标准差情况，以评估图像的平整度/噪声水平。

## What Changes
- 在完整流程的测试数据处理中计算每张图像的平面标准差
- 计算补偿前后所有图像标准差的平均值
- 在结果面板中显示这两个新指标
- 在日志中输出这两个值

## Impact
- Affected specs: ui-application
- Affected code: ui/app.py
