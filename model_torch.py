import torch
import torch.nn as nn
from torchvision.models.resnet import BasicBlock

#模型
class EarlyExitResNet18(nn.Module):
    def __init__(self, num_classes=78):
        super(EarlyExitResNet18, self).__init__()

        # Initial layers
        self.conv1 = nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.relu = nn.ReLU(inplace=True)
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)

        # ResNet18 stages with proper downsampling (block数分别为2/2/2/2)
        self.stage1 = self._make_layer(64, 64, 2)
        self.stage2 = self._make_layer(64, 128, 2, stride=2)
        self.stage3 = self._make_layer(128, 256, 2, stride=2)
        self.stage4 = self._make_layer(256, 512, 2, stride=2)

        # Early exits
        self.exit1 = self._make_exit(64, num_classes)
        self.exit2 = self._make_exit(128, num_classes)
        self.exit3 = self._make_exit(256, num_classes)
        self.exit4 = self._make_exit(512, num_classes)

        # Initialize weights
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)

    def _make_layer(self, in_channels, out_channels, blocks, stride=1):
        downsample = None
        if stride != 1 or in_channels != out_channels:
            downsample = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(out_channels),
            )

        layers = []
        layers.append(BasicBlock(in_channels, out_channels, stride, downsample))
        for _ in range(1, blocks):
            layers.append(BasicBlock(out_channels, out_channels))

        return nn.Sequential(*layers)

    def _make_exit(self, in_channels, num_classes):
        return nn.Sequential(
            nn.AdaptiveAvgPool2d((1, 1)),
            nn.Flatten(),
            nn.Linear(in_channels, num_classes)
        )

    def forward(self, x, target_stage=None):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)

        x = self.stage1(x)
        if target_stage == 1:
            return self.exit1(x)

        x = self.stage2(x)
        if target_stage == 2:
            return self.exit2(x)

        x = self.stage3(x)
        if target_stage == 3:
            return self.exit3(x)

        x = self.stage4(x)
        return self.exit4(x)

    def forward_train(self, x):
        outputs = []

        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)

        # Stage 1
        x = self.stage1(x)
        outputs.append(self.exit1(x))

        # Stage 2
        x = self.stage2(x)
        outputs.append(self.exit2(x))

        # Stage 3
        x = self.stage3(x)
        outputs.append(self.exit3(x))

        # Stage 4 (final)
        x = self.stage4(x)
        outputs.append(self.exit4(x))

        return outputs