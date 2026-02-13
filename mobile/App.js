/**
 * KD-Code Mobile Application
 * React Native structure for iOS/Android
 */

import React, { useState, useEffect } from 'react';
import {
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  View,
  TextInput,
  TouchableOpacity,
  Image,
  Alert,
  PermissionsAndroid,
  Platform,
} from 'react-native';

import { RNCamera } from 'react-native-camera';
import RNFS from 'react-native-fs';

const App = () => {
  const [text, setText] = useState('');
  const [kdCodeImage, setKdCodeImage] = useState(null);
  const [scannedText, setScannedText] = useState('');
  const [isScanning, setIsScanning] = useState(false);

  // Function to generate KD-Code
  const generateKdCode = async () => {
    if (!text.trim()) {
      Alert.alert('Error', 'Please enter text to encode');
      return;
    }

    try {
      const response = await fetch('http://your-api-url/api/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: text }),
      });

      const data = await response.json();
      if (data.status === 'success') {
        setKdCodeImage(`data:image/png;base64,${data.image}`);
      } else {
        Alert.alert('Error', data.error || 'Failed to generate KD-Code');
      }
    } catch (error) {
      console.error('Error generating KD-Code:', error);
      Alert.alert('Error', 'Failed to generate KD-Code');
    }
  };

  // Function to handle barcode scanning
  const handleBarcodeDetected = ({ barcodes }) => {
    if (barcodes.length > 0) {
      const barcode = barcodes[0];
      setScannedText(barcode.data);
      setIsScanning(false);
    }
  };

  // Request camera permissions
  useEffect(() => {
    const requestCameraPermission = async () => {
      if (Platform.OS === 'android') {
        try {
          const granted = await PermissionsAndroid.request(
            PermissionsAndroid.PERMISSIONS.CAMERA,
            {
              title: 'Camera Permission',
              message: 'App needs access to camera to scan KD-Codes.',
              buttonNeutral: 'Ask Me Later',
              buttonNegative: 'Cancel',
              buttonPositive: 'OK',
            },
          );
          if (granted !== PermissionsAndroid.RESULTS.GRANTED) {
            Alert.alert('Permission Denied', 'Camera permission is required to scan KD-Codes.');
          }
        } catch (err) {
          console.warn(err);
        }
      }
    };

    requestCameraPermission();
  }, []);

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor="#f8f9fa" />
      
      <ScrollView contentInsetAdjustmentBehavior="automatic" style={styles.scrollView}>
        <View style={styles.header}>
          <Text style={styles.title}>KD-Code System</Text>
          <Text style={styles.subtitle}>Mobile Application</Text>
        </View>

        {/* Generator Section */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Generate KD-Code</Text>
          
          <TextInput
            style={styles.input}
            placeholder="Enter text or URL to encode..."
            value={text}
            onChangeText={setText}
            multiline
            numberOfLines={3}
          />
          
          <TouchableOpacity style={styles.button} onPress={generateKdCode}>
            <Text style={styles.buttonText}>Generate KD-Code</Text>
          </TouchableOpacity>
          
          {kdCodeImage && (
            <View style={styles.codeContainer}>
              <Image source={{ uri: kdCodeImage }} style={styles.codeImage} />
            </View>
          )}
        </View>

        {/* Scanner Section */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Scan KD-Code</Text>
          
          {!isScanning ? (
            <TouchableOpacity 
              style={[styles.button, styles.scanButton]} 
              onPress={() => setIsScanning(true)}
            >
              <Text style={styles.buttonText}>Start Scanner</Text>
            </TouchableOpacity>
          ) : (
            <View style={styles.cameraContainer}>
              <RNCamera
                style={styles.preview}
                onBarCodeRead={handleBarcodeDetected}
                permissionDialogTitle="Permission to use camera"
                permissionDialogMessage="We need your permission to use your camera to scan KD-Codes"
                barCodeTypes={[RNCamera.Constants.BarCodeType.qr]}
              />
              <TouchableOpacity 
                style={[styles.button, styles.stopButton]} 
                onPress={() => setIsScanning(false)}
              >
                <Text style={styles.buttonText}>Stop Scanner</Text>
              </TouchableOpacity>
            </View>
          )}
          
          {scannedText ? (
            <View style={styles.resultContainer}>
              <Text style={styles.resultLabel}>Scanned Result:</Text>
              <Text style={styles.resultText}>{scannedText}</Text>
            </View>
          ) : null}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  scrollView: {
    flex: 1,
  },
  header: {
    alignItems: 'center',
    paddingVertical: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#dee2e6',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#212529',
  },
  subtitle: {
    fontSize: 16,
    color: '#6c757d',
    marginTop: 5,
  },
  section: {
    padding: 20,
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#495057',
    marginBottom: 15,
  },
  input: {
    borderWidth: 1,
    borderColor: '#ced4da',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    backgroundColor: '#fff',
    marginBottom: 15,
    minHeight: 100,
  },
  button: {
    backgroundColor: '#0d6efd',
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderRadius: 8,
    alignItems: 'center',
    marginBottom: 15,
  },
  scanButton: {
    backgroundColor: '#198754',
  },
  stopButton: {
    backgroundColor: '#dc3545',
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  codeContainer: {
    alignItems: 'center',
    marginTop: 15,
  },
  codeImage: {
    width: 200,
    height: 200,
    resizeMode: 'contain',
  },
  cameraContainer: {
    alignItems: 'center',
  },
  preview: {
    width: '100%',
    height: 300,
    justifyContent: 'flex-end',
    alignItems: 'center',
  },
  resultContainer: {
    marginTop: 15,
    padding: 15,
    backgroundColor: '#e9ecef',
    borderRadius: 8,
  },
  resultLabel: {
    fontWeight: '600',
    color: '#495057',
    marginBottom: 5,
  },
  resultText: {
    color: '#212529',
    fontSize: 16,
  },
});

export default App;